import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng gọn gàng, chuyên nghiệp
st.set_page_config(
    page_title="Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính")
st.markdown("Ứng dụng tự động phân tích dữ liệu, tính toán chỉ số **VPD**, bắt bệnh môi trường nhà kính theo **7 trường hợp toàn diện**.")

# =====================================================================
# 1. ĐỊNH NGHĨA CÁC HÀM XỬ LÝ LOGIC TRUNG TÂM
# =====================================================================

def calculate_vpd(temp, humi):
    """
    [VÒNG 1 - TÍNH VPD TRƯỚC]: Tính toán chỉ số VPD (kPa) từ Nhiệt độ và Độ ẩm không khí
    Sử dụng công thức Tetens chuẩn vật lý.
    """
    # Áp suất hơi bão hòa (Saturated Vapor Pressure)
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    # Thiếu hụt áp suất hơi nước (Vapor Pressure Deficit)
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)


def analyze_7_cases(vpd, temp, humi, station_id, t_col_name, h_col_name):
    """
    [VÒNG 2 - PHÂN LOẠI SAU]: Nhận giá trị số từ cột VPD đã tính để xếp nhóm
    Trả về: (Mã nhóm viết tắt, Tên trạng thái, Màu sắc, Nguyên nhân, Giải pháp, Là_Lỗi)
    """
    # --- THÀNH PHẦN NGOẠI LỆ (LỖI THIẾT BỊ / DỮ LIỆU) ---
    if pd.isna(temp) or pd.isna(humi):
        return pd.Series([
            "Loi",
            "Lỗi dữ liệu khuyết thiếu", 
            "gray", 
            f"Khuyết thiếu thông số đo trên cột [{t_col_name}] hoặc [{h_col_name}].", 
            "Kiểm tra lại log truyền nhận dữ liệu của thiết bị.", 
            True
        ])
    
    # CHẶN TRÊN: Nếu nhiệt độ KK > 55°C (vượt giới hạn vật lý tự nhiên của khí hậu) -> Báo lỗi thiết bị
    if temp < -5 or temp > 55 or humi < 1 or humi > 100:
        return pd.Series([
            "Loi",
            "Lỗi thiết bị (Out of Range)", 
            "gray", 
            f"Giá trị bất thường tại [Trạm {station_id}]: Cột [{t_col_name}]={temp}°C hoặc [{h_col_name}]. Ghim nhận thông số vượt ngưỡng tự nhiên (Cảm biến dính nắng trực tiếp hoặc treo mạch).", 
            "Bỏ qua mốc tính toán này. Vui lòng kiểm tra, vệ sinh hoặc thay thế đầu dò cảm biến khí hậu ngoài nhà kính.", 
            True
        ])
    
    # --- THÀNH PHẦN SINH LÝ CÂY TRỒNG & VẬN HÀNH ---
    # Trường hợp 5: Độ ẩm đạt ngưỡng bão hòa 100%
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            "TH5",
            f"Trường hợp 5: Bão hòa hơi nước (VPD: {vpd} kPa)", 
            "darkred", 
            f"Không khí đạt trạng thái bão hòa ẩm hoàn toàn (Độ ẩm cột [{h_col_name}] đạt {humi}%). Thường xảy ra ban đêm hoặc mưa kéo dài liên tục.", 
            "Cảnh báo đọng sương gây nấm bệnh! Kích hoạt quạt đối lưu và quạt hút ép ẩm ra ngoài; mở bớt cửa thông gió; tuyệt đối ngừng tưới; bật sưởi nâng nhiệt nếu là ban đêm.",
            False
        ])
        
    # Trường hợp 1: VPD Quá Thấp (< 0.4 kPa)
    elif vpd < 0.4:
        return pd.Series([
            "TH1",
            f"Trường hợp 1: VPD Quá Thấp (VPD: {vpd} kPa)", 
            "red", 
            f"Độ ẩm không khí quá cao ({humi}%) hoặc nhiệt độ sụt thấp. Cây bị nghẹn rễ, không thể thoát hơi nước qua lá để hút dinh dưỡng lên thân.", 
            "Bật quạt đối lưu điều hòa không khí; ngừng phun sương làm mát; mở bớt mái che hoặc mở cửa hông nhà kính để thoát ẩm.",
            False
        ])
        
    # Trường hợp 2: VPD Thấp Tối Ưu (0.4 đến 0.8 kPa)
    elif 0.4 <= vpd < 0.8:
        return pd.Series([
            "TH2",
            f"Trường hợp 2: Thấp Tối Ưu (VPD: {vpd} kPa)", 
            "blue", 
            "Môi trường vi khí hậu ẩm dịu mát, chênh lệch áp suất hơi nước nhẹ nhàng, an toàn.", 
            "Điều kiện hoàn hảo cho giai đoạn kích rễ, nuôi cây mô hoặc cây con mới ra vườn giúp lá không bị mất nước. Tiếp tục duy trì ổn định.",
            False
        ])
        
    # Trường hợp 3: Cao Tối Ưu (0.8 đến 1.2 kPa)
    elif 0.8 <= vpd <= 1.2:
        return pd.Series([
            "TH3",
            f"Trường hợp 3: Cao Tối Ưu (VPD: {vpd} kPa)", 
            "green", 
            "Sự cân bằng tuyệt vời giữa nhiệt độ ngày và độ ẩm. Khí khổng mở tối đa.", 
            "Vùng vàng kích hoạt năng suất cao nhất cho cây trưởng thành quang hợp mạnh và hấp thụ phân bón tốt nhất. Duy trì chế độ vận hành.",
            False
        ])
        
    # Trường hợp 4: VPD Quá Cao (> 1.2 kPa)
    else:
        return pd.Series([
            "TH4",
            f"Trường hợp 4: VPD Quá Cao (VPD: {vpd} kPa)", 
            "orange", 
            f"Nhiệt độ không khí quá cao ({temp}°C) hoặc không khí quá khô hanh (Độ ẩm sụt sâu còn {humi}%). Cây bị stress nặng, phải đóng khí khổng tự vệ để giữ nước.", 
            "Kích hoạt ngay hệ thống phun sương bù ẩm; kéo lưới cắt nắng giảm bức xạ nhiệt trực tiếp; tăng cường tưới nhỏ giọt dưới gốc cấp nước cho rễ.",
            False
        ])


# =====================================================================
# 2. KHU VỰC ĐỌC VÀ XỬ LÝ FILE DỮ LIỆU JSON TRÊN GIAO DIỆN
# =====================================================================

uploaded_file = st.file_uploader("Kéo thả file dữ liệu quan trắc thực địa dạng JSON vào đây để phân tích", type=["json"])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data)
        
        original_columns = list(df.columns)
        time_col = None
        stt_col = None
        
        # Tự động quét tìm cột Thời gian và cột định danh Trạm (STT)
        for col in original_columns:
            col_lower = col.lower()
            if col_lower in ['thời gian', 'thoigian', 'time', 'timestamp', 'date']:
                time_col = col
            if col_lower in ['stt', 'station', 'id', 'tram', 'trạm']:
                stt_col = col
                
        if not time_col:
            st.error("⚠️ Không tìm thấy cột chứa dữ liệu Thời gian trong file.")
        elif not stt_col:
            st.error("⚠️ Không tìm thấy cột định danh Trạm hoặc STT trong file.")
        else:
            # Giữ nguyên chuỗi thời gian văn bản thô để tránh xung đột định dạng dấu gạch ngang (-)
            df[time_col] = df[time_col].astype(str)
            
            # [Trường hợp 7]: Tách riêng Trạm khí hậu 5 và cách ly các trạm đo đất (1, 2, 3)
            df_air = df[df[stt_col].astype(str) == "5"].copy()
            
            total_rows = len(df)
            station_5_rows = len(df_air)
            other_station_rows = total_rows - station_5_rows
            
            # Tự động nhận diện cột Nhiệt độ KK và Độ ẩm KK (tempKK, humiKK)
            t_col = None
            h_col = None
            for col in df_air.columns:
                col_lower = col.lower()
                if col_lower in ['tempkk', 'temp_kk', 'nhietdokk', 'temp']:
                    t_col = col
                if col_lower in ['humikk', 'humi_kk', 'doamkk', 'humi']:
                    h_col = col
            
            if not t_col or not h_col:
                st.error("⚠️ Không tìm thấy cột dữ liệu Nhiệt độ không khí (tempKK) hoặc Độ ẩm không khí (humiKK) trong file.")
            else:
                # Ép kiểu dữ liệu dạng số số học, loại bỏ các dòng lỗi khuyết thiếu dữ liệu
                df_air[t_col] = pd.to_numeric(df_air[t_col], errors='coerce')
                df_air[h_col] = pd.to_numeric(df_air[h_col], errors='coerce')
                df_air = df_air.dropna(subset=[t_col, h_col])
                
                # --- [BƯỚC CHUẨN HOÁ LOGIC]: TÍNH TOÁN CHỈ SỐ VPD TRƯỚC ---
                df_air['VPD (kPa)'] = calculate_vpd(df_air[t_col], df_air[h_col]).round(3)
                
                # --- [BƯỚC TIẾP THEO]: PHÂN LOẠI TRƯỜNG HỢP DỰA TRÊN CỘT VPD VỪA TÍNH ---
                df_air[['Ma_TH', 'Trạng thái', 'Màu sắc', 'Nguyên nhân', 'Giải pháp', 'Là_Lỗi']] = df_air.apply(
                    lambda row: analyze_7_cases(row['VPD (kPa)'], row[t_col], row[h_col], row[stt_col], t_col, h_col), axis=1
                )
                
                # Sắp xếp trục tiến trình thời gian tăng dần từ ngày đầu tiên trở đi
                df_air = df_air.sort_values(by=time_col, ascending=True)
                
                # --- THÀNH PHẦN 1: GIAO DIỆN THỐNG KÊ TỔNG QUAN TỶ LỆ ---
                st.subheader("📊 Báo Cáo Phân Phối Trạng Thái Nhà Kính Tổng Thể")
                
                valid_air_df = df_air[df_air['Là_Lỗi'] == False]
                total_valid = len(valid_air_df) if len(valid_air_df) > 0 else 1
                counts = valid_air_df['Ma_TH'].value_counts()
                
                def get_pct(code_name):
                    return (counts.get(code_name, 0) / total_valid) * 100

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("⚫ TH5: Bão Hòa Ẩm", f"{get_pct('TH5'):.1f}%")
                col2.metric("🔴 TH1: VPD Quá Thấp", f"{get_pct('TH1'):.1f}%")
                col3.metric("🔵 TH2: Thấp Tối Ưu", f"{get_pct('TH2'):.1f}%")
                col4.metric("🟢 TH3: Cao Tối Ưu", f"{get_pct('TH3'):.1f}%")
                col5.metric("🟠 TH4: VPD Quá Cao", f"{get_pct('TH4'):.1f}%")
                
                st.info(f"💡 **Trường hợp 7 (Cách ly hệ thống):** Tìm thấy {other_station_rows} dòng dữ liệu của các cảm biến đất (STT 1,2,3) trong file. Hệ thống đã tự động cách ly an toàn, dữ liệu phân tích chỉ xử lý riêng cho {station_5_rows} dòng của trạm khí hậu 5.")
                
                # --- THÀNH PHẦN 2: MENU LỰA CHỌN CỐ ĐỊNH TINH GỌN (CHỈ 6 DÒNG) ---
                st.subheader("🔍 Bộ Lọc Phân Tách Trường Hợp")
                
                case_options = {
                    "ALL": "Xem tất cả các mốc dòng dữ liệu ghi nhận trong file",
                    "TH4": "Trường hợp 4: VPD Quá Cao (Cây Stress khô nóng)",
                    "TH5": "Trường hợp 5: Bão hòa hơi nước (VPD = 0 kPa, Nguy cơ đọng sương)",
                    "TH1": "Trường hợp 1: VPD Quá Thấp (Không khí quá ẩm, nghẹn rễ)",
                    "TH3": "Trường hợp 3: Cao Tối Ưu (Vùng quang hợp mạnh tốt nhất)",
                    "TH2": "Trường hợp 2: Thấp Tối Ưu (Vùng ẩm dịu mát cho cây con)",
                    "Loi": "Các mốc thời gian phát hiện lỗi thiết bị / nhiệt độ vượt ngưỡng 55°C"
                }
                
                selected_label = st.selectbox(
                    "Chọn duy nhất một nhóm trường hợp cố định để bung (show) danh sách chi tiết dưới dạng bảng:",
                    options=list(case_options.values()),
                    index=0
                )
                
                # Tìm ngược lại mã nhóm viết tắt (ALL, TH4, TH5...) dựa vào dòng chữ được bấm chọn
                selected_code = [k for k, v in case_options.items() if v == selected_label][0]
                
                # --- THÀNH PHẦN 3: BUNG DANH SÁCH CHI TIẾT BẰNG BẢNG CUỘN THEO LỰA CHỌN ---
                st.subheader("📋 Bảng Trích Xuất Mốc Thời Gian Chi Tiết")
                
                if selected_code == "ALL":
                    display_df = df_air.copy()
                else:
                    display_df = df_air[df_air['Ma_TH'] == selected_code].copy()
                
                if display_df.empty:
                    st.success("🎉 Không tìm thấy mốc thời gian nào thuộc nhóm trạng thái này trong file dữ liệu của bạn.")
                else:
                    st.write(f"Tìm thấy **{len(display_df)}** dòng dữ liệu thỏa mãn điều kiện lọc:")
                    
                    # Trình bày dữ liệu dạng bảng cuộn (Dataframe) cực kỳ gọn gàng, chống lỗi tràn hoặc quá tải giao diện
                    st.dataframe(
                        display_df[[time_col, t_col, h_col, 'VPD (kPa)', 'Trạng thái', 'Nguyên nhân', 'Giải pháp']], 
                        use_container_width=True
                    )
                            
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
