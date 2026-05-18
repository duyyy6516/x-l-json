import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng chuyên nghiệp, sạch sẽ
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
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)

def analyze_7_cases(temp, humi, station_id, t_col_name, h_col_name):
    """
    Phân loại chi tiết dữ liệu đầu vào dựa trên 7 trường hợp vận hành thực tế
    Trả về: (Trạng thái, Màu hiển thị, Nguyên nhân chi tiết, Giải pháp đề xuất, Có_Phải_Lỗi)
    """
    # --- THÀNH PHẦN NGOẠI LỆ (LỖI THIẾT BỊ / DỮ LIỆU) ---
    if pd.isna(temp) or pd.isna(humi):
        return pd.Series([
            "Lỗi dữ liệu", 
            "gray", 
            f"Bản ghi tại [Trạm {station_id}] bị khuyết thiếu thông số đo đạc trên cột [{t_col_name}] hoặc [{h_col_name}].", 
            "Bỏ qua dòng này. Kiểm tra lại kết nối và log truyền nhận dữ liệu của thiết bị.", 
            True
        ])
    
    # KIỂM TRA GIỚI HẠN VẬT LÝ AN TOÀN RIÊNG CHO MÔI TRƯỜNG KHÔNG KHÍ TẠI TRẠM ĐO KHÍ HẬU
    if temp < -5 or temp > 55 or humi < 1 or humi > 100:
        return pd.Series([
            "Lỗi thiết bị (Out of Range)", 
            "gray", 
            f"Phát hiện giá trị bất thường tại [Trạm {station_id}]: Cột [{t_col_name}] ghi nhận số [{temp}°C] hoặc Cột [{h_col_name}] ghi nhận số [{humi}%] vượt quá giới hạn môi trường tự nhiên.", 
            f"Bỏ qua mốc tính toán này. Vui lòng kiểm tra, vệ sinh đầu dò cảm biến hoặc kiểm tra lại cấu trúc cấu hình dải đo của [Trạm {station_id}].", 
            True
        ])
    
    # Tính VPD cho dữ liệu hợp lệ
    vpd = round(calculate_vpd(temp, humi), 3)
    
    # --- THÀNH PHẦN SINH LÝ CÂY TRỒNG & VẬN HÀNH ---
    # Trường hợp 5: Độ ẩm bão hòa hoàn toàn (Độ ẩm đạt 100%, VPD = 0)
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            f"Trường hợp 5: Bão hòa hơi nước (VPD: {vpd} kPa)", 
            "darkred", 
            f"Môi trường tại [Trạm {station_id}] đạt trạng thái bão hòa ẩm hoàn toàn (Độ ẩm cột [{h_col_name}] = {humi}%). Thường xảy ra vào ban đêm, khi trời mưa kéo dài hoặc phun sương quá mức.", 
            "Cảnh báo nguy cơ đọng sương gây nấm bệnh cực cao! Kích hoạt ngay quạt đối lưu và quạt hút để ép ẩm ra ngoài; mở bớt cửa thông gió; tuyệt đối ngừng tưới; nếu là ban đêm hãy bật hệ thống sưởi nâng nhiệt để giảm ẩm bão hòa.",
            False
        ])
        
    # Trường hợp 1: VPD Quá Thấp (VPD < 0.4 kPa)
    elif vpd < 0.4:
        return pd.Series([
            f"Trường hợp 1: VPD Quá Thấp (VPD: {vpd} kPa)", 
            "red", 
            f"Tại [Trạm {station_id}]: Độ ẩm cột [{h_col_name}] đang quá cao ({humi}%) hoặc nhiệt độ cột [{t_col_name}] hạ thấp ({temp}°C). Cây bị nghẹn rễ, lực hút yếu và không thể thoát hơi nước để nhận dinh dưỡng.", 
            "Bật quạt đối lưu điều hòa không khí; ngừng toàn bộ hệ thống phun sương làm mát; mở bớt mái che hoặc mở cửa hông nhà kính để thoát ẩm tồn đọng.",
            False
        ])
        
    # Trường hợp 2: VPD Thấp Tối Ưu (0.4 <= VPD < 0.8 kPa)
    elif 0.4 <= vpd < 0.8:
        return pd.Series([
            f"Trường hợp 2: Thấp Tối Ưu (VPD: {vpd} kPa)", 
            "blue", 
            f"Môi trường tại [Trạm {station_id}] ẩm dịu mát (Nhiệt độ: {temp}°C, Độ ẩm: {humi}%), chênh lệch áp suất hơi nước nhẹ nhàng, an toàn.", 
            "Điều kiện hoàn hảo cho giai đoạn kích rễ, nuôi cây mô hoặc cây con mới ra vườn giúp tránh mất nước qua lá. Tiếp tục duy trì ổn định hệ thống.",
            False
        ])
        
    # Trường hợp 3: Cao Tối Ưu (0.8 <= VPD <= 1.2 kPa)
    elif 0.8 <= vpd <= 1.2:
        return pd.Series([
            f"Trường hợp 3: Cao Tối Ưu (VPD: {vpd} kPa)", 
            "green", 
            f"Môi trường tại [Trạm {station_id}] đạt sự cân bằng tuyệt vời (Nhiệt độ: {temp}°C, Độ ẩm: {humi}%). Khí khổng mở tối đa để hấp thụ CO2.", 
            "Vùng vàng kích hoạt năng suất cao nhất cho cây trưởng thành quang hợp và hấp thụ phân bón (Canxi, Magiê) tốt nhất. Duy trì các chế độ vận hành hiện tại.",
            False
        ])
        
    # Trường hợp 4: VPD Quá Cao (VPD > 1.2 kPa)
    else:
        return pd.Series([
            f"Trường hợp 4: VPD Quá Cao (VPD: {vpd} kPa)", 
            "orange", 
            f"Tại [Trạm {station_id}]: Nhiệt độ cột [{t_col_name}] quá cao ({temp}°C) hoặc độ ẩm cột [{h_col_name}] sụt giảm sâu còn {humi}%. Cây bị stress nặng, phải đóng khí khổng tự vệ, ngừng quang hợp.", 
            "Kích hoạt ngay hệ thống phun sương bù ẩm; kéo lưới cắt nắng (lưới lan) giảm bức xạ nhiệt trực tiếp; tăng cường tưới nhỏ giọt dưới gốc cấp nước cho rễ.",
            False
        ])

# 2. KHU VỰC TẢI FILE DỮ LIỆU JSON
uploaded_file = st.file_uploader("Kéo thả file dữ liệu quan trắc thực địa dạng JSON vào đây để phân tích", type=["json"])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data)
        
        # Lưu lại danh sách tên cột gốc ban đầu
        original_columns = list(df.columns)
        
        # Khởi tạo các biến dò cột động cho Thời gian và STT trạm
        time_col = None
        stt_col = None
        
        # Tự động quét tìm cột chứa "Thời gian" và "STT"
        for col in original_columns:
            col_lower = col.lower()
            if col_lower in ['thời gian', 'thoigian', 'time', 'timestamp', 'date']:
                time_col = col
            if col_lower in ['stt', 'station', 'id', 'tram', 'trạm']:
                stt_col = col
                
        if not time_col:
            st.error("⚠️ Không tìm thấy cột chứa dữ liệu Thời gian trong file của bạn (Hệ thống tìm theo các tên chuẩn: 'Thời gian', 'thoigian', 'time').")
        elif not stt_col:
            st.error("⚠️ Không tìm thấy cột định danh Trạm hoặc STT trong file.")
        else:
            # --- XỬ LÝ ĐỊNH DẠNG THỜI GIAN ĐỂ CHỐNG LỖI SẮP XẾP ---
            df[time_col] = df[time_col].astype(str).str.replace(r'(\d{2})-(\d{2})-(\d{2})$', r'\1:\2:\3', regex=True)
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            
            # Tách riêng biệt: Lọc Trạm đo không khí (STT == "5") để tính VPD
            df_air = df[df[stt_col].astype(str) == "5"].copy()
            
            total_rows = len(df)
            station_5_rows = len(df_air)
            other_station_rows = total_rows - station_5_rows
            
            # Tự động tìm cột nhiệt độ không khí (tempKK) và độ ẩm không khí (humiKK)
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
                # Ép kiểu dữ liệu dạng số (float) cho nhiệt độ và độ ẩm không khí trạm 5
                df_air[t_col] = pd.to_numeric(df_air[t_col], errors='coerce')
                df_air[h_col] = pd.to_numeric(df_air[h_col], errors='coerce')
                
                # Loại bỏ các dòng trống hoàn toàn dữ liệu đo của trạm khí hậu trước khi phân tích
                df_air = df_air.dropna(subset=[t_col, h_col])
                
                # Tiến hành phân tích cấu trúc trường hợp và truyền tên cột thực tế vào hàm để tạo câu thông báo động
                df_air[['Trạng thái', 'Màu sắc', 'Nguyên nhân', 'Giải pháp', 'Là_Lỗi']] = df_air.apply(
                    lambda row: analyze_7_cases(row[t_col], row[h_col], row[stt_col], t_col, h_col), axis=1
                )
                
                # Định dạng lại chuỗi thời gian hiển thị trên giao diện
                df_air['ThoiGian_HienThi'] = df_air[time_col].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # --- PHẦN 1: DASHBOARD THỐNG KÊ TỔNG QUAN ---
                st.subheader("📊 Báo Cáo Phân Phối Trạng Thái Nhà Kính (Trạm Đo Khí Hậu 5)")
                
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
                
                # Hiển thị thông báo bóc tách Trường hợp 7 (Chỉ rõ số dòng và số trạm đất cụ thể)
                st.info(f"💡 **Trường hợp 7 (Hệ thống phân tách dữ liệu):** Tìm thấy {other_station_rows} dòng dữ liệu thuộc các trạm đo đất (STT 1, 2, 3). Hệ thống đã tự động cách ly phân loại nhóm này và chỉ tập trung xử lý tính toán chuyên sâu cho {station_5_rows} dòng dữ liệu vi khí hậu của trạm 5.")
                
                # --- PHẦN 2: DANH SÁCH BẮT BỆNH VÀ HIỂN THỊ GIẢI PHÁP CHI TIẾT ---
                st.subheader("⚠️ Log Cảnh Báo Vi Khí Hậu & Hướng Dẫn Xử Lý Kỹ Thuật")
                st.markdown("Danh sách chi tiết các mốc thời gian vi khí hậu bất thường nguy cơ cao (Sắp xếp xuôi dòng thời gian từ ngày cũ đến ngày mới):")
                
                # Lọc ra các mốc cần phải đưa ra cảnh báo hành động
                alert_conditions = df_air['Trạng thái'].str.contains("Trường hợp 5|Trường hợp 1|Trường hợp 4|Lỗi")
                alerts_df = df_air[alert_conditions].sort_values(by=time_col, ascending=True)
                
                if alerts_df.empty:
                    st.success("🎉 Xin chúc mừng! Hệ thống kiểm tra toàn bộ dữ liệu và thấy môi trường nhà kính luôn duy trì ở trạng thái tối ưu lý tưởng.")
                else:
                    for _, row in alerts_df.iterrows():
                        display_time = row['ThoiGian_HienThi']
                        status_str = row['Trạng thái']
                        color = row['Màu sắc']
                        reason_str = row['Nguyên nhân']
                        sol_str = row['Giải pháp']
                        
                        if color == "darkred":
                            st.error(f"❌ **⏰ Thời gian: {display_time}** | **{status_str}**")
                            st.write(f"🔍 **Chi tiết phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục:** {sol_str}")
                            st.markdown("---")
                        elif color == "red":
                            st.error(f"🚨 **⏰ Thời gian: {display_time}** | **{status_str}**")
                            st.write(f"🔍 **Chi tiết phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục:** {sol_str}")
                            st.markdown("---")
                        elif color == "orange":
                            st.warning(f"⚠️ **⏰ Thời gian: {display_time}** | **{status_str}**")
                            st.write(f"🔍 **Chi tiết phân tích:** {reason_str}")
                            st.write(f"🛠️ **Biện pháp khắc phục:** {sol_str}")
                            st.markdown("---")
                        elif color == "gray":
                            st.info(f"⚙️ **⏰ Thời gian: {display_time}** | **{status_str}**")
                            st.write(f"🔍 **Chi tiết lỗi hệ thống:** {reason_str}")
                            st.write(f"🛠️ **Hướng dẫn xử lý phần cứng:** {sol_str}")
                            st.markdown("---")
                            
                # --- PHẦN 3: XEM TOÀN BỘ BẢNG DỮ LIỆU GỐC ĐÃ XỬ LÝ ---
                with st.expander("🔍 Xem chi tiết toàn bộ bảng dữ liệu phân tích đầy đủ (Xếp từ ngày cũ đến ngày mới)"):
                    df_full_sorted = df_air.sort_values(by=time_col, ascending=True)
                    st.dataframe(df_full_sorted[['ThoiGian_HienThi', stt_col, t_col, h_col, 'Trạng thái']], use_container_width=True)
                    
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
