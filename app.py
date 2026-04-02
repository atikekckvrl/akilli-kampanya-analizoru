import pandas as pd
import gradio as gr
import tempfile
import os
from openpyxl import load_workbook

# =========================
# Excel Görünüm Ayarları
# =========================
def adjust_excel_format(path):
    wb = load_workbook(path)
    ws = wb.active

    for col in ws.columns:
        max_len = 2
        col_letter = col[0].column_letter

        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))

        # Sütun genişliğini ayarla
        ws.column_dimensions[col_letter].width = min(max_len + 3, 50)

        # Başlığa göre format belirle
        header = str(col[0].value).lower()
        if "spend" in header or "oran" in header:
            for cell in col[1:]:
                cell.number_format = "0.00%"
        elif any(x in header for x in ["budget", "cost", "cpa", "kpi", "cast", "maaliyet"]):
            for cell in col[1:]:
                cell.number_format = '#,##0.00'

    wb.save(path)

# =========================
# Ana Hesaplama Algoritması
# =========================
import traceback

# =========================
# Ana Hesaplama Algoritması
# =========================
def process_excel(file):
    try:
        if file is None:
            return None, None
            
        print(f"Dosya işleniyor: {file.name}")
        df = pd.read_excel(file.name)
        original_columns = df.columns.tolist()

        # ... (rest of the logic remains the same) ...
        # (I will keep the logic I implemented previously but with the try block)
        
        # Kolon isimlerini normalize et
        def find_col(possible_names):
            for name in df.columns:
                if str(name).strip().lower() in [p.lower() for p in possible_names]:
                    return name
            return None

        cols = {
            "camp_budget": find_col(["Camp budget", "Camp. budget"]),
            "camp_cost": find_col(["Camp cast", "Camp. cost", "Camp cost"]),
            "camp_3d_cost": find_col(["Camp 3d cast", "Camp. 3D cost", "Camp 3d cost"]),
            "camp_conv": find_col(["Camp conv", "Camp. conv.", "Camp conv."]),
            "camp_cpa": find_col(["Camp cpa", "Camp. CPA", "Camp cpa"]),
            "label_budget": find_col(["Label budget"]),
            "label_cost": find_col(["Label cost"]),
            "label_3d_cost": find_col(["Label 3d cost", "Label 3D cost"]),
            "label_kpi": find_col(["Label kpı value", "Label KPI value", "Label KPI"]),
            "label_cpa": find_col(["Label cpa", "Label CPA"]),
            "labels_on_camp": find_col(["Labels on campaign", "Labels on Campaign"]),
            "camp_name": find_col(["Campaign name"])
        }

        for k, v in cols.items():
            if v is None:
                df[k] = "" if k in ["labels_on_camp", "camp_name"] else 0.0
                cols[k] = k
            else:
                if k in ["labels_on_camp", "camp_name"]:
                    # String kolonları için güvenli dönüşüm
                    df[v] = df[v].astype(str).replace('nan', '')
                else:
                    # Sayısal kolonlar için dönüşüm
                    df[v] = pd.to_numeric(df[v], errors="coerce").fillna(0)

        for col in ["MTD Cluster Spend", "Label remaining budget", "New daily budget", "New target CPA"]:
            if col not in df.columns:
                df[col] = 0.0

        for label, group in df.groupby(cols["labels_on_camp"]):
            idxs = group.index
            # Boş etiketleri atla
            if not str(label).strip():
                continue
                
            l_budget = group[cols["label_budget"]].iloc[0]
            l_cost = group[cols["label_cost"]].iloc[0]
            l_3d = group[cols["label_3d_cost"]].iloc[0]
            l_kpi = group[cols["label_kpi"]].iloc[0]
            l_cpa = group[cols["label_cpa"]].iloc[0]

            days_passed = l_cost / l_3d if l_3d > 0 else 15
            days_passed = min(max(days_passed, 1), 29)
            remaining_days = 30 - days_passed

            l_rem_daily = max(l_budget - l_cost, 0) / remaining_days if remaining_days > 0 else 0
            df.loc[idxs, "Label remaining budget"] = round(l_rem_daily, 2)

            target_mtd = (l_budget / 30) * days_passed
            is_lagging = l_cost < target_mtd * 0.85
            new_target_cpa = l_kpi * 1.15 if is_lagging else l_kpi
            new_target_cpa = max(new_target_cpa, 0.01)
            df.loc[idxs, "New target CPA"] = round(new_target_cpa, 2)

            total_l_cost = group[cols["camp_cost"]].sum()
            if total_l_cost > 0:
                df.loc[idxs, "MTD Cluster Spend"] = group[cols["camp_cost"]] / total_l_cost

            # 4. New Daily Budget
            daily_allocations = {}
            total_allocated_label = 0
            for i, row in group.iterrows():
                name = str(row[cols["camp_name"]])
                budget_val = row[cols["camp_budget"]]
                cost_val = row[cols["camp_cost"]]
                progression = days_passed / 30
                expected_mtd = budget_val * progression
                is_suitable = cost_val >= (expected_mtd * 0.8) if expected_mtd > 0 else True
                
                total_l_3d_costs = group[cols["camp_3d_cost"]].sum()
                weight = row[cols["camp_3d_cost"]] / total_l_3d_costs if total_l_3d_costs > 0 else 1/len(group)
                
                base = l_rem_daily * weight
                if not is_suitable: base *= 0.7
                if "prem" in name.lower(): base *= 1.1
                elif "devp" in name.lower(): base *= 0.9
                
                daily_allocations[i] = base
                total_allocated_label += base

            if total_allocated_label > 0:
                target_range_min = l_rem_daily * 0.85
                target_range_max = l_rem_daily * 1.15
                if total_allocated_label < target_range_min:
                    adjustment = target_range_min / total_allocated_label
                elif total_allocated_label > target_range_max:
                    adjustment = target_range_max / total_allocated_label
                else: adjustment = 1.0
                for i in daily_allocations: daily_allocations[i] *= adjustment

            # India Cap
            india_cap = l_budget * 0.30
            # Camp name'in seri bazlı string erişimi için asType zaten yapıldı
            india_mtd = group[group[cols["camp_name"]].str.contains("India", case=False, na=False)][cols["camp_cost"]].sum()
            india_daily_lim = max(india_cap - india_mtd, 0) / remaining_days if remaining_days > 0 else 0
            india_alloc = 0
            for i, row in group.iterrows():
                name = str(row[cols["camp_name"]])
                val = daily_allocations[i]
                if "india" in name.lower():
                    allowed = max(india_daily_lim - india_alloc, 0)
                    val = min(val, allowed)
                    india_alloc += val
                df.at[i, "New daily budget"] = round(max(val, 5), 2)

        # Kaydet
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"optimize_sonuc_{timestamp}.xlsx"
        
        # Çalışma dizinini al ve dosya adıyla birleştir
        # os.path.abspath ve os.path.join kullanarak 'İ' karakterini daha güvenli yönetelim
        cwd = os.getcwd()
        output_path = os.path.join(cwd, out_name)
        
        # Pandas ve Openpyxl ile kaydet
        df.to_excel(output_path, index=False)
        adjust_excel_format(output_path)
        
        print(f"İşlem başarıyla tamamlandı: {output_path}")
        return output_path, output_path

    except Exception as e:
        print("HATA OLUŞTU!")
        traceback.print_exc()
        return None, None

# =========================
# UI (Premium Design)
# =========================

# Modern CSS with Glassmorphism and Professional Color Palette
css_code = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');

footer {visibility: hidden}

.gradio-container {
    background: linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%);
    font-family: 'Outfit', sans-serif !important;
}

.main-header {
    text-align: center;
    padding: 2.5rem 0;
    margin-bottom: 2rem;
    background: rgba(255, 255, 255, 0.4);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.5);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}

.main-header h1 {
    color: #102a43;
    font-weight: 600;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    letter-spacing: -0.5px;
}

.main-header p {
    color: #486581;
    font-weight: 400;
    font-size: 1.1rem;
}

.section-card {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
    transition: transform 0.2s ease;
}

.section-card:hover {
    transform: translateY(-2px);
}

#calc-btn {
    background: linear-gradient(90deg, #243b55 0%, #141e30 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.5rem !important;
    font-size: 1.1rem !important;
    box-shadow: 0 4px 15px rgba(20, 30, 48, 0.3) !important;
    transition: all 0.3s ease !important;
}

#calc-btn:hover {
    box-shadow: 0 6px 20px rgba(20, 30, 48, 0.4) !important;
    filter: brightness(1.1);
}

#dl-btn {
    background: white !important;
    color: #102a43 !important;
    border: 2px solid #102a43 !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
}

.rules-accordion {
    border: none !important;
    background: transparent !important;
}
"""

with gr.Blocks(title="Bütçe Optimizasyon v2.0") as demo:
    with gr.Column(elem_classes="main-header"):
        gr.HTML(
            """
            <h1>🎯 Akıllı Kampanya Analizörü</h1>
            <p>Bütçe & CPA Optimizasyonu İçin Gelişmiş Dağıtım Algoritması</p>
            """
        )
    
    with gr.Row():
        with gr.Column(scale=1, elem_classes="section-card"):
            gr.Markdown("### 📤 1. Adım: Veri Kaynağı")
            file_in = gr.File(
                label="Excel Dosyasını Sürükleyin veya Seçin", 
                file_types=[".xlsx"],
                elem_id="input-file"
            )
            gr.Markdown("<small>Not: .xlsx formatında, kampanya verilerini içeren dosya gereklidir.</small>")
            btn = gr.Button("📊 Hesaplamayı Başlat ve Optimize Et", variant="primary", elem_id="calc-btn")
            
        with gr.Column(scale=1, elem_classes="section-card"):
            gr.Markdown("### 📥 2. Adım: Sonuç ve Analiz")
            file_out = gr.File(label="Hazırlanan Optimizasyon Dosyası", interactive=False)
            dl = gr.DownloadButton("💾 Excel Dosyasını İndir", variant="secondary", elem_id="dl-btn")
            gr.Markdown("<small>Tablo openpyxl ile otomatik olarak biçimlendirilmiştir.</small>")

    with gr.Row():
        with gr.Accordion("🔍 Uygulanan Zeki Algoritma Kuralları", open=False, elem_classes="rules-accordion"):
            gr.Markdown(
                """
                | Kural Kategorisi | Detaylı Açıklama |
                | :--- | :--- |
                | **P1: KPI Önceliği** | Harcama gerideyse Target CPA, KPI değerinin %115'ine kadar otomatik esnetilir. |
                | **P2: Bütçe Dengesi** | Kalan bütçe, son 3 günlük harcama performansına göre paylaştırılır (+/- %15 tolerans). |
                | **P3: Bölgesel Sınır** | Hindistan kampanyalarına toplam etiket bütçesinin max %30'u atanır. |
                | **Verim Kontrolü** | Bütçesini harcamayan kampanyalarda (H/C < %80) otomatik kısıntı yapılır. |
                | **Güvenlik Katmanı** | Min günlük bütçe 5 olarak korunur; CPA değerleri asla 0 olmaz. |
                """
            )

    btn.click(fn=process_excel, inputs=file_in, outputs=[file_out, dl])

if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="indigo"), 
        css=css_code
    )
