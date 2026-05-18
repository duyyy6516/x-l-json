import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng sạch sẽ, chuyên nghiệp
st.set_page_config(
    page_title="Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Hệ Thống Phân Tích & Cảnh Báo VPD Nhà Kính")
st.markdown("Ứng dụng tự động phân tích dữ liệu, tính toán chỉ số **VPD**, bắt bệnh môi trường nhà kính theo **7 trường hợp toàn diện** và đề xuất giải pháp kỹ thuật cụ thể.")

# 1. ĐỊNH NGHĨA LOGIC PHÂN TÍCH TOÀN DIỆN (7 TRƯỜNG HỢP)
def calculate_vpd(temp, humi):
    """Tính toán chỉ số VPD (kPa) từ Nhiệt độ (°C) và Độ ẩm (%)"""
    # Công thức Tetens tính Áp suất hơi bão hòa (Saturated Vapor Pressure)
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    # Tính Thiếu hụt áp suất hơi nước (Vapor Pressure Deficit)
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)

def analyze_7_cases(temp, humi):
    """
    Phân loại chi tiết dữ liệu đầu vào dựa trên 7 trường hợp vận hành thực tế
    Trả về: (Trạng thái, Màu hiển thị, Nguyên nhân chi tiết, Giải pháp đề xuất, Có_Phải_Lỗi)
    """
    # --- THÀNH PHẦN NGOẠI LỆ (LỖI THIẾT BỊ / DỮ LIỆU) ---
    # Trường hợp 6: Lỗi cảm biến hoặc giá trị vượt giới hạn vật lý tự nhiên
    if pd.isna(temp) or pd.isna(humi):
        return pd.Series(["Lỗi dữ liệu", "gray", "Bản ghi bị khuyết thiếu thông số Nhiệt độ hoặc Độ ẩm.", "Bỏ qua dòng này. Kiểm tra lại log truyền nhận dữ liệu.", True])
    
    if temp < -10 or temp > 60 or humi < 0 or humi > 100:
        return pd.Series(["Lỗi thiết bị (Out of Range)", "gray", f"Cảm biến trả về giá trị bất thường (Nhiệt độ: {temp}°C, Độ ẩm: {humi}%). Có thể đầu dò bị treo hoặc dính nước.", "Bỏ qua mốc tính toán này. Vui lòng kiểm tra, vệ sinh hoặc thay thế đầu dò cảm biến khí hậu.", True])
    
    # Tính VPD cho dữ liệu hợp lệ
    vpd = round(calculate_vpd(temp, humi), 3)
    
    # --- THÀNH PHẦN SINH LÝ CÂY TRỒNG & VẬN HÀNH ---
    # Trường hợp 5: Độ ẩm bão hòa hoàn toàn (Độ ẩm đạt 100%, VPD = 0)
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            f"Trường hợp 5: Bão hòa hơi nước (VPD: {vpd} kPa)", 
            "darkred", 
            "Không khí đạt trạng thái bão hòa ẩm hoàn toàn (Độ ẩm 100%). Thường xảy ra vào ban đêm, khi trời mưa kéo dài hoặc phun sương quá mức.", 
            "Cảnh báo nguy cơ đọng sương gây nấm bệnh! Kích hoạt ngay quạt đối lưu và quạt hút để ép ẩm ra ngoài; mở cửa thông gió; tuyệt đối ngừng tưới; nếu là ban đêm hãy bật hệ thống sưởi nâng nhiệt để giảm ẩm bão hòa.",
            False
        ])
        
    # Trường hợp 1: VPD Quá Thấp (VPD < 0.4 kPa)
    elif vpd < 0.4:
        return pd.Series([
            f"Trường hợp 1: VPD Quá Thấp (VPD: {vpd} kPa)", 
            "red", 
            f"Độ ẩm không khí quá cao ({humi}%) hoặc nhiệt độ hạ thấp ({temp}°C). Cây bị nghẹn rễ, không thể thoát hơi nước để hút dinh dưỡng.", 
            "Bật quạt đối lưu điều hòa không khí; ngừng toàn bộ hệ thống phun sương làm mát; mở bớt mái che hoặc cửa hông để thoát ẩm.",
            False
        ])
        
    # Trường hợp 2: VPD Thấp Tối Ưu (0.4 <= VPD < 0.8 kPa)
    elif 0.4 <= vpd < 0.8:
        return pd.Series([
            f"Trường hợp 2: Thấp Tối Ưu (VPD: {vpd} kPa)", 
            "blue", 
            "Môi trường vi khí hậu ẩm dịu mát, chênh lệch áp suất hơi nước nhẹ nhàng.", 
            "Điều kiện hoàn hảo cho giai đoạn kích rễ, nuôi cây mô hoặc cây con mới ra vườn giúp tránh mất nước qua lá. Tiếp tục duy trì ổn định.",
            False
        ])
        
    # Trường hợp 3: Cao Tối Ưu (0.8 <= VPD <= 1.2 kPa)
    elif 0.8 <= vpd <= 1.2:
        return pd.Series([
            f"Trường hợp 3: Cao Tối Ưu (VPD: {vpd} kPa)", 
            "green", 
            "Sự cân bằng tuyệt vời giữa nhiệt độ ngày và độ ẩm. Khí khổng mở tối đa.", 
            "Vùng vàng kích hoạt năng suất cao nhất cho cây trưởng thành quang hợp và hấp thụ phân bón (Canxi, Magiê). Duy trì các chế độ vận hành hiện tại.",
            False
        ])
        
    # Trường hợp 4: VPD Quá Cao (VPD > 1.2 kPa)
    else:
        return pd.Series([
            f"Trường hợp 4: VPD Quá Cao (VPD: {vpd} kPa)", 
            "orange", 
            f"Nhiệt độ không khí quá cao ({temp}°C) hoặc không khí khô hanh (Độ ẩm sụt giảm sâu còn {humi}%). Cây bị stress nặng, phải đóng khí khổng tự vệ, ngừng quang hợp.", 
            "Kích hoạt ngay hệ thống phun sương bù ẩm; kéo lưới cắt nắng giảm bức xạ nhiệt; tăng cường tưới nhỏ giọt dưới gốc cấp nước cho rễ.",
            False
        ])

# 2. KHU VỰC TẢI FILE DỮ LIỆU JSON
uploaded_file = st.file_uploader("Kéo thả file dữ liệu 'Quan trắc thực địa.json' vào đây để chạy thử", type=["json"])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data)
        
        # Trường hợp 7: Trạm không có dữ liệu khí hậu (Lọc dữ liệu vi khí hậu)
        if 'STT' not in df.columns or 'Thời gian' not in df.columns:
            st.error("Cấu trúc file không đúng định dạng kiểm thử hệ thống (Thiếu cột STT hoặc Thời gian).")
        else:
            # Lọc riêng dữ liệu vi khí hậu của trạm STT == "5"
            df_air = df[df['STT'] == "5"].copy()
            
            # Tính toán số lượng dòng thuộc trạm khác (Trường hợp 7)
            total_rows = len(df)
            station_5_rows = len(df_air)
            other_station_rows = total_rows - station_5_rows
            
            # Chuyển đổi định dạng số cho cột nhiệt độ, độ ẩm không khí
            df_air['tempKK'] = pd.to_numeric(df_air['tempKK'], errors='coerce')
            df_air['humiKK'] = pd.to_numeric(df_air['humiKK'], errors='coerce')
            
            # Áp dụng hàm phân tích 7 trường hợp
            df_air[['Trạng thái', 'Màu sắc', 'Nguyên nhân', 'Giải pháp', 'Là_Lỗi']] = df_air.apply(
                lambda row: analyze_7_cases(row['tempKK'], row['humiKK']), axis=1
            )
            
            # --- PHẦN 1: DASHBOARD THỐNG KÊ TỔNG QUAN ---
            st.subheader("📊 Báo Cáo Phân Phối Trạng Thái Nhà Kính")
            
            # Tính toán phần trăm phân bổ (loại bỏ dòng lỗi phần cứng khi tính sinh lý)
            valid_air_df = df_air[df_air['Là_Lỗi'] == False]
            total_valid = len(valid_air_df) if len(valid_air_df) > 0 else 1
            
            counts = valid_air_df['Trạng thái'].value_counts()
            
            def get_pct(name_contains):
                match = [c for c in counts.index if name_contains in c]
                return (counts.get(match[0], 0) / total_valid) * 100 if match else 0.0

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("⚫ TH5: Bão Hòa Ẩm", f"{get_pct('Trường hợp 5'):.1f}%")
            col2.metric("🔴 TH1: VPD Quá Thấp", f"{get_pct('Trường hợp 1'):.1f}%")
            col3.metric("🔵 TH2: Thấp Tối Ưu", f"{get_pct('Trường hợp 2'):.1f}%")
            col4.metric("🟢 TH3: Cao Tối Ưu", f"{get_pct('Trường hợp 3'):.1f}%")
            col5.metric("🟠 TH4: VPD Quá Cao", f"{get_pct('Trường hợp 4'):.1f}%")
            
            # Hiển thị thông báo về Trường hợp 7 (Mất đồng bộ trạm đất)
            st.info(f"💡 **Trường hợp 7 (Hệ thống phân tách dữ liệu):** Tìm thấy {other_station_rows} dòng dữ liệu thuộc các trạm đo đất (STT 1, 2, 3). Hệ thống đã tự động phân loại cách ly và chỉ tập trung xử lý {station_5_rows} dòng dữ liệu của trạm khí hậu.")
            
            # --- PHẦN 2: DANH SÁCH BẮT BỆNH VÀ HIỂN THỊ GIẢI PHÁP CHI TIẾT ---
            st.subheader("⚠️ Log Cảnh Báo Vi Khí Hậu & Hướng Dẫn Xử Lý Kỹ Thuật")
            st.markdown("Hệ thống liệt kê danh sách các mốc thời gian vi khí hậu bất thường nguy cơ cao (Sắp xếp từ mới nhất trở về trước):")
            
            # Lọc các dòng cần cảnh báo khẩn cấp (TH5 bão hòa, TH1 quá thấp, TH4 quá cao, hoặc lỗi thiết bị)
            alert_conditions = df_air['Trạng thái'].str.contains("Trường hợp 5|Trường hợp 1|Trường hợp 4|Lỗi")
            alerts_df = df_air[alert_conditions].sort_values(by='Thời gian', ascending=False)
            
            if alerts_df.empty:
                st.success("🎉 Xin chúc mừng! Hệ thống kiểm tra toàn bộ file dữ liệu và thấy môi trường nhà kính luôn duy trì ở trạng thái tối ưu lý tưởng.")
            else:
                # Duyệt qua các bản ghi lỗi để "bắt bệnh" và in giải pháp ra giao diện
                for _, row in alerts_df.iterrows():
                    time_str = row['Thời gian']
                    status_str = row['Trạng thái']
                    color = row['Màu sắc']
                    reason_str = row['Nguyên nhân']
                    sol_str = row['Giải pháp']
                    
                    # Sử dụng khối hộp container trực quan theo màu quy định
                    if color == "darkred":
                        with st.container():
                            st.error(f"❌ **⏰ {time_str}** | **{status_str}**")
                            st.write(f"🔍 **Lý do hệ thống phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục nhà kính:** {sol_str}")
                            st.markdown("---")
                    elif color == "red":
                        with st.container():
                            st.error(f"🚨 **⏰ {time_str}** | **{status_str}**")
                            st.write(f"🔍 **Lý do hệ thống phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục nhà kính:** {sol_str}")
                            st.markdown("---")
                    elif color == "orange":
                        with st.container():
                            st.warning(f"⚠️ **⏰ {time_str}** | **{status_str}**")
                            st.write(f"🔍 **Lý do hệ thống phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục nhà kính:** {sol_str}")
                            st.markdown("---")
                    elif color == "gray":
                        with st.container():
                            st.info(f"⚙️ **⏰ {time_str}** | **{status_str}**")
                            st.write(f"🔍 **Chi tiết lỗi phần cứng:** {reason_str}")
                            st.write(f"🛠️ **Hướng dẫn xử lý phần cứng:** {sol_str}")
                            st.markdown("---")
                            
            # --- PHẦN 3: XEM TOÀN BỘ BẢNG DỮ LIỆU GỐC ĐÃ XỬ LÝ ---
            with st.expander("🔍 Xem chi tiết bảng dữ liệu phân tích đầy đủ"):
                st.dataframe(df_air[['Thời gian', 'STT', 'tempKK', 'humiKK', 'Trạng thái']], use_container_width=True)
                
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
