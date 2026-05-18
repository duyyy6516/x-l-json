import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng gọn gàng, chuyên nghiệp
st.set_page_config(
    page_title="Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính Đa Trạm",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính - Phiên Bản Đa Trạm")
st.markdown("Ứng dụng tự động phân tích dữ liệu, tự động chuyển đổi cấu hình để tính toán chỉ số **VPD** cho cả Trạm Khí Hậu (STT 5) và các Trạm Đo Đất (STT 1, 2, 3, 4).")

# =====================================================================
# 1. ĐỊNH NGHĨA CÁC HÀM XỬ LÝ LOGIC TRUNG TÂM
# =====================================================================

def calculate_vpd(temp, humi):
    """
    Tính toán chỉ số VPD (kPa) từ Nhiệt độ và Độ ẩm
    Sử dụng công thức Tetens chuẩn vật lý.
    """
    # Áp suất hơi bão hòa (Saturated Vapor Pressure)
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    # Thiếu hụt áp suất hơi nước (Vapor Pressure Deficit)
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)


def analyze_7_cases(vpd, temp, humi, station_id, t_col_name, h_col_name):
    """
    Phân loại chi tiết dữ liệu dựa trên giá trị VPD đã tính
    """
    if pd.isna(temp) or pd.isna(humi):
        return pd.Series([
            "Loi", "Lỗi dữ liệu khuyết thiếu", "gray", 
            f"Khuyết thiếu thông số đo trên cột [{t_col_name}] hoặc [{h_col_name}].", 
            "Kiểm tra lại log truyền nhận dữ liệu của thiết bị.", True
        ])
    
    # ĐIỀU CHỈNH GIỚI HẠN LỌC LỖI: Trạm 5 chặn 55°C, trạm đất (1,2,3,4) nâng lên 400°C để giữ lại dữ liệu thô
    max_temp_limit = 55 if str(station_id) == "5" else 400
    
    if temp < -5 or temp > max_temp_limit or humi < 0 or humi > 100:
        return pd.Series([
            "Loi", "Lỗi thiết bị (Out of Range)", "gray", 
            f"Giá trị vượt ngưỡng vật lý an toàn: [{t_col_name}]={temp}°C, [{h_col_name}]={humi}%.", 
            f"Kiểm tra lại cấu hình phần cứng hoặc đầu dò của Trạm {station_id}.", True
        ])
    
    # Phân loại trạng thái dựa trên chỉ số VPD
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            "TH5", f"Trường hợp 5: Bão hòa hơi nước (VPD: {vpd} kPa)", "darkred", 
            f"Môi trường đạt trạng thái bão hòa ẩm hoàn toàn (Độ ẩm đạt {humi}%).", 
            "Nguy cơ đọng sương/ứ nước cực cao! Kích hoạt ngay hệ thống thông gió bóc tách ẩm khẩn cấp.", False
        ])
    elif vpd < 0.4:
        return pd.Series([
            "TH1", f"Trường hợp 1: Chỉ số Quá Thấp (VPD: {vpd} kPa)", "red", 
            f"Môi trường quá ẩm ướt (Độ ẩm: {humi}%, Nhiệt độ: {temp}°C). Tốc độ thoát hơi nước bị ngưng trệ.", 
            "Cần điều chỉnh giảm lượng nước tưới; tăng lưu thông gió để làm thoáng môi trường.", False
        ])
    elif 0.4 <= vpd < 0.8:
        return pd.Series([
            "TH2", f"Trường hợp 2: Thấp Tối Ưu (VPD: {vpd} kPa)", "blue", 
            "Môi trường dịu mát, độ ẩm an toàn lý tưởng.", 
            "Rất thích hợp cho các giai đoạn rễ non, cây con phát triển hoặc phục hồi sức khỏe ổn định.", False
        ])
    elif 0.8 <= vpd <= 1.2:
        return pd.Series([
            "TH3", f"Trường hợp 3: Cao Tối Ưu (VPD: {vpd} kPa)", "green", 
            "Sự cân bằng tuyệt vời giữa nhiệt độ và độ ẩm.", 
            "Vùng năng suất cao nhất, giúp quá trình trao đổi chất và hấp thụ dinh dưỡng diễn ra mạnh mẽ nhất.", False
        ])
    else:
        return pd.Series([
            "TH4", f"Trường hợp 4: Chỉ số Quá Cao (VPD: {vpd} kPa)", "orange", 
            f"Nhiệt độ tăng cao ({temp}°C) hoặc độ ẩm sụt giảm sâu xuống mức hanh khô ({humi}%).", 
            "Môi trường bị stress khô hạn! Kích hoạt ngay hệ thống cấp nước bù ẩm, tưới nhỏ giọt hạ nhiệt.", False
        ])

# =====================================================================
# 2. KHU VỰC ĐỌC FILE VÀ CẤU HÌNH GIAO DIỆN CHỌN TRẠM
# =====================================================================

uploaded_file = st.file_uploader("Kéo thả file dữ liệu 'Quan trắc thực địa.json' vào đây", type=["json"])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data)
        
        # Dò tìm cột Thời gian và cột định danh Trạm (STT)
        time_col = None
        stt_col = None
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['thời gian', 'thoigian', 'time', 'timestamp', 'date']:
                time_col = col
            if col_lower in ['stt', 'station', 'id', 'tram', 'trạm']:
                stt_col = col
                
        if not time_col or not stt_col:
            st.error("⚠️ File JSON thiếu cột định danh 'STT' hoặc 'Thời gian' chuẩn hệ thống.")
        else:
            df[time_col] = df[time_col].astype(str)
            
            # Lấy danh sách tất cả các Trạm thực tế có trong file dữ liệu của bạn
            available_stations = sorted(df[stt_col].astype(str).unique())
            
            # --- THANH CẤU HÌNH CHỌN TRẠM ĐỂ TÍNH TOÁN ---
            st.subheader("⚙️ Cấu Hình Trạm Tính Toán Chỉ Số")
            selected_station = st.selectbox(
                "Chọn số Trạm (STT) bạn muốn áp dụng thuật toán tính toán:",
                options=available_stations,
                index=0
            )
            
            # Lọc riêng dữ liệu của Trạm đã được chọn
            df_selected = df[df[stt_col].astype(str) == selected_station].copy()
            st.success(f"Đang xử lý dữ liệu cho **Trạm {selected_station}** (Tìm thấy {len(df_selected)} dòng dữ liệu).")
            
            # --- TỰ ĐỘNG ĐỔI CỘT TÙY THEO TRẠM ĐƯỢC CHỌN ---
            t_col, h_col = None, None
            
            if selected_station == "5":
                # Nếu chọn trạm 5: Quét tìm cột không khí tempKK, humiKK
                for col in df_selected.columns:
                    if col.lower() in ['tempkk', 'temp_kk', 'nhietdokk', 'temp']: t_col = col
                    if col.lower() in ['humikk', 'humi_kk', 'doamkk', 'humi']: h_col = col
            else:
                # Nếu chọn trạm 1, 2, 3, 4: Quét tìm cột đo đất có dấu 'Nhiệt Độ', 'Độ ẩm'
                for col in df_selected.columns:
                    if col in ['Nhiệt Độ', 'nhietdo', 'nhiệt độ']: t_col = col
                    if col in ['Độ ẩm', 'doam', 'độ ẩm']: h_col = col
            
            if not t_col or not h_col:
                st.error(f"⚠️ Trạm {selected_station} không chứa đủ cặp cột thông số đo để tính toán chỉ số (Yêu cầu cột Nhiệt độ và Độ ẩm).")
            else:
                st.info(f"📊 Đối chiếu thành công: Sử dụng cột **[{t_col}]** làm Nhiệt độ và cột **[{h_col}]** làm Độ ẩm.")
                
                # Ép kiểu dữ liệu số và làm sạch dòng trống
                df_selected[t_col] = pd.to_numeric(df_selected[t_col], errors='coerce')
                df_selected[h_col] = pd.to_numeric(df_selected[h_col], errors='coerce')
                df_selected = df_selected.dropna(subset=[t_col, h_col])
                
                # Chạy quy trình toán học chuẩn: Tính VPD trước -> Phân loại sau
                df_selected['VPD (kPa)'] = calculate_vpd(df_selected[t_col], df_selected[h_col]).round(3)
                
                df_selected[['Ma_TH', 'Trạng thái', 'Màu sắc', 'Nguyên nhân', 'Giải pháp', 'Là_Lỗi']] = df_selected.apply(
                    lambda row: analyze_7_cases(row['VPD (kPa)'], row[t_col], row[h_col], row[stt_col], t_col, h_col), axis=1
                )
                
                df_selected = df_selected.sort_values(by=time_col, ascending=True)
                
                # --- HIỂN THỊ KẾT QUẢ PHÂN PHỐI TỶ LỆ ---
                st.subheader(f"📊 Báo Cáo Phân Phối Trạng Thái Toàn Diện - Trạm {selected_station}")
                valid_df = df_selected[df_selected['Là_Lỗi'] == False]
                total_valid = len(valid_df) if len(valid_df) > 0 else 1
                counts = valid_df['Ma_TH'].value_counts()
                
                def get_pct(code_name):
                    return (counts.get(code_name, 0) / total_valid) * 100

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("⚫ TH5: Bão Hòa Ẩm", f"{get_pct('TH5'):.1f}%")
                col2.metric("🔴 TH1: Chỉ số Quá Thấp", f"{get_pct('TH1'):.1f}%")
                col3.metric("🔵 TH2: Thấp Tối Ưu", f"{get_pct('TH2'):.1f}%")
                col4.metric("🟢 TH3: Cao Tối Ưu", f"{get_pct('TH3'):.1f}%")
                col5.metric("🟠 TH4: Chỉ số Quá Cao", f"{get_pct('TH4'):.1f}%")
                
                # --- BỘ LỌC XEM TỪNG TRƯỜNG HỢP CỐ ĐỊNH ---
                st.subheader("🔍 Bộ Lọc Phân Tách Nhóm")
                case_options = {
                    "ALL": "Xem tất cả các mốc dòng dữ liệu trích xuất của trạm này",
                    "TH4": "Trường hợp 4: Chỉ số Quá Cao (Stress khô nóng/Hanh khô)",
                    "TH5": "Trường hợp 5: Bão hòa hơi nước (VPD = 0 kPa)",
                    "TH1": "Trường hợp 1: Chỉ số Quá Thấp (Môi trường quá ẩm)",
                    "TH3": "Trường hợp 3: Cao Tối Ưu (Trạng thái cân bằng tốt cực đại)",
                    "TH2": "Trường hợp 2: Thấp Tối Ưu (Trạng thái ẩm dịu mát)",
                    "Loi": "Các mốc thời gian ghi nhận lỗi thiết bị / vượt ngưỡng vật lý"
                }
                selected_label = st.selectbox(
                    "Chọn duy nhất một nhóm trường hợp cố định để bung bảng chi tiết:",
                    options=list(case_options.values()), index=0
                )
                selected_code = [k for k, v in case_options.items() if v == selected_label][0]
                
                # Hiển thị bảng kết quả cuộn
                st.subheader("📋 Bảng Trích Xuất Mốc Thời Gian Chi Tiết")
                if selected_code == "ALL":
                    display_df = df_selected.copy()
                else:
                    display_df = df_selected[df_selected['Ma_TH'] == selected_code].copy()
                
                if display_df.empty:
                    st.success("🎉 Không tìm thấy mốc thời gian nào thuộc nhóm trạng thái này.")
                else:
                    st.write(f"Tìm thấy **{len(display_df)}** dòng dữ liệu:")
                    
                    # Cấu hình danh sách cột hiển thị linh hoạt theo trạm đất/không khí cho bảng dữ liệu gọn gàng
                    base_cols = [time_col, t_col, h_col, 'VPD (kPa)', 'Trạng thái', 'Nguyên nhân', 'Giải pháp']
                    st.dataframe(display_df[base_cols], use_container_width=True)
                            
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
