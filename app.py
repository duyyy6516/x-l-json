import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng tối giản
st.set_page_config(
    page_title="Hệ Thống Tin Nhắn Cảnh Báo Nhà Kính",
    page_icon="📱",
    layout="wide"
)

st.title("📱 Hệ Thống Tin Nhắn Cảnh Báo Nhà Kính Tự Động")
st.markdown("Ứng dụng tự động xử lý file, tính chỉ số bốc hơi và dịch nghĩa thành **tin nhắn báo động gửi về điện thoại** cho người dân.")

def calculate_vpd(temp, humi):
    """Tính toán chỉ số VPD (kPa) từ Nhiệt độ và Độ ẩm theo công thức Tetens"""
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)

def analyze_environment_details(vpd, temp, humi, station_id):
    """
    Biến đổi dữ liệu thành câu thông báo dạng tin nhắn SMS gửi về điện thoại cho người dân.
    """
    stt_str = str(station_id)
    
    # 1. Kiểm tra lỗi mất kết nối (Độ ẩm bằng 0)
    if humi == 0:
        return pd.Series([
            "Mất tín hiệu thiết bị",
            f"Trạm {stt_str} đang báo độ ẩm bằng 0%. Có thể bị lỏng giắc cắm hoặc đứt dây nguồn.",
            "Ra vườn kiểm tra lại dây cáp, rút ra cắm lại cục cảm biến."
        ])
    
    # 2. Kiểm tra trạng thái bão hòa ẩm (Độ ẩm quá cao)
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            "Không khí ẩm ướt bão hòa",
            f"Trạm {stt_str} báo độ ẩm chạm trần {humi}%. Nhà kính quá bí bách, nước đọng vách màng.",
            "Bật ngay quạt hút để đuổi ẩm ra ngoài, tuyệt đối không được tưới thêm nước."
        ])
    
    # 3. Kiểm tra trạng thái không khí quá ẩm ướt
    if vpd < 0.4:
        return pd.Series([
            "Nhà kính quá ẩm",
            f"Độ ẩm trạm {stt_str} đang cao ({humi}%), trời lạnh mát. Cây bị nghẹn rễ, không hút được phân.",
            "Bật quạt đối lưu để thoáng khí, mở bớt cửa hông hoặc mái che để thoát bớt hơi ẩm."
        ])
    
    # 4. Kiểm tra trạng thái Thấp Tối Ưu
    if 0.4 <= vpd < 0.8:
        return pd.Series([
            "Môi trường mát mẻ lý tưởng",
            f"Trạm {stt_str} ghi nhận không khí mát mẻ, ẩm dịu mát an toàn.",
            "Rất tốt cho bầu rễ và cây con mới trồng. Cứ tiếp tục duy trì chăm sóc bình thường."
        ])
    
    # 5. Kiểm tra trạng thái Cao Tối Ưu
    if 0.8 <= vpd <= 1.2:
        return pd.Series([
            "Thời tiết hoàn hảo",
            f"Trạm {stt_str} đạt độ ẩm và nhiệt độ cân bằng. Lá cây mở khỏe, ăn phân mạnh nhất.",
            "Thời điểm vàng để cây lớn và nuôi quả. Cứ giữ nguyên chế độ vườn hiện tại."
        ])
    
    # 6. Kiểm tra trạng thái Khô Nóng Gắt (Phần lớn dữ liệu của bạn rơi vào đây)
    if temp > 40.0 and humi < 40.0:
        return pd.Series([
            "CẢNH BÁO: KHÔ NÓNG GẮT",
            f"Trạm {stt_str} báo nhiệt độ vọt lên {temp}°C, trời quá hanh khô ({humi}%). Lá cây đang bị héo.",
            "Chạy ra kéo ngay lưới lan đen cắt nắng, bật phun sương làm mát không khí khẩn cấp."
        ])
    elif humi < 40.0:
        return pd.Series([
            "Môi trường quá khô hanh",
            f"Trạm {stt_str} báo độ ẩm tụt sâu còn {humi}%. Không khí khô làm lá bị mất nước nhanh.",
            "Bật hệ thống phun sương giữa vườn để bù lại độ ẩm cho không khí."
        ])
    else:
        return pd.Series([
            "Nhiệt độ tăng cao",
            f"Trạm {stt_str} báo trời bị hầm nóng ({temp}°C), đẩy áp suất bốc hơi lên ngưỡng cao.",
            "Tăng thêm thời gian tưới nhỏ giọt dưới gốc để cấp đủ nước cho rễ hút làm mát thân."
        ])

# Khu vực tải file dữ liệu JSON
uploaded_file = st.file_uploader("Kéo thả file dữ liệu JSON vào đây để quét tin nhắn cảnh báo", type=["json"])

if uploaded_file is not None:
    try:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data)
        
        # Tự động dò tìm cột Thời gian và cột STT trạm
        time_col = None
        stt_col = None
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['thời gian', 'thoigian', 'time', 'timestamp', 'date']: time_col = col
            if col_lower in ['stt', 'station', 'id', 'tram', 'trạm']: stt_col = col
                
        if not time_col or not stt_col:
            st.error("⚠️ File JSON không chứa cột định danh 'STT' hoặc 'Thời gian'.")
        else:
            df[time_col] = df[time_col].astype(str)
            df[stt_col] = df[stt_col].astype(str)
            
            processed_chunks = []
            
            # Duyệt qua từng Trạm để bóc tách dữ liệu
            for station_id in df[stt_col].unique():
                sub_df = df[df[stt_col] == station_id].copy()
                
                t_col, h_col = None, None
                
                if station_id == "5":
                    # Trạm 5 không khí: tempKK và humiKK
                    for col in sub_df.columns:
                        if col.lower() in ['tempkk', 'temp_kk', 'nhietdokk', 'temp']: t_col = col
                        if col.lower() in ['humikk', 'humi_kk', 'doamkk', 'humi']: h_col = col
                    
                    if t_col and h_col:
                        sub_df[t_col] = pd.to_numeric(sub_df[t_col], errors='coerce')
                        sub_df[h_col] = pd.to_numeric(sub_df[h_col], errors='coerce')
                        
                else:
                    # Trạm 1, 2, 3, 4 đất: Đồng bộ cột Nhiệt độ và Độ ẩm
                    if 'Nhiệt Độ' in sub_df.columns or 'Nhiệt độ' in sub_df.columns:
                        s_temp = pd.Series(np.nan, index=sub_df.index)
                        if 'Nhiệt Độ' in sub_df.columns: s_temp = s_temp.fillna(sub_df['Nhiệt Độ'])
                        if 'Nhiệt độ' in sub_df.columns: s_temp = s_temp.fillna(sub_df['Nhiệt độ'])
                        sub_df['Nhiệt_Độ_Đất'] = pd.to_numeric(s_temp, errors='coerce')
                        t_col = 'Nhiệt_Độ_Đất'
                    
                    for col in sub_df.columns:
                        if col in ['Độ ẩm', 'doam', 'độ ẩm']: 
                            sub_df['Độ_Ẩm_Đất'] = pd.to_numeric(sub_df[col], errors='coerce')
                            h_col = 'Độ_Ẩm_Đất'
                    
                    # Quy đổi số thô về số thực thực tế cho các trạm đất (chia 10)
                    if t_col and h_col:
                        sub_df[t_col] = sub_df[t_col].apply(lambda x: x / 10.0 if x > 100 else x)
                        sub_df[h_col] = sub_df[h_col].apply(lambda x: x / 10.0 if x > 100 else x)
                
                if t_col and h_col:
                    sub_df = sub_df.dropna(subset=[t_col, h_col])
                    if not sub_df.empty:
                        # Bước 1: Tính toán chỉ số VPD trước
                        sub_df['VPD (kPa)'] = calculate_vpd(sub_df[t_col], sub_df[h_col]).round(3)
                        
                        # Bước 2: Biên dịch trực tiếp thành các nội dung tin nhắn SMS
                        sub_df[['Trạng Thái Vườn', 'Lý Do Từ Cảm Biến', 'Hành Động Khắc Phục']] = sub_df.apply(
                            lambda row: analyze_environment_details(row['VPD (kPa)'], row[t_col], row[h_col], row[stt_col]), axis=1
                        )
                        
                        # Giữ lại các cột theo cấu trúc bảng sạch tinh gọn
                        sub_cols = [time_col, station_id, 'VPD (kPa)', 'Trạng Thái Vườn', 'Lý Do Từ Cảm Biến', 'Hành Động Khắc Phục']
                        # Thay đổi tên cột số trạm động thành cột cố định
                        sub_df = sub_df.rename(columns={stt_col: "Số Trạm"})
                        processed_chunks.append(sub_df[["Thời gian", "Số Trạm", "VPD (kPa)", "Trạng Thái Vườn", "Lý Do Từ Cảm Biến", "Hành Động Khắc Phục"]])
            
            # Gộp chung dữ liệu các trạm và xuất ra bảng tổng hợp duy nhất
            if processed_chunks:
                final_df = pd.concat(processed_chunks, ignore_index=True)
                final_df = final_df.sort_values(by=time_col, ascending=True)
                
                st.subheader("📋 Nhật Ký Tin Nhắn Cảnh Báo Gửi Về Điện Thoại")
                st.write(f"Tổng số tin nhắn hệ thống đã biên soạn: **{len(final_df)}** mốc cảnh báo.")
                
                # Hiển thị bảng sạch cấu trúc phân tách rõ ràng ra giao diện người dùng
                st.dataframe(final_df, use_container_width=True)
            else:
                st.warning("⚠️ Không thể trích xuất dữ liệu Nhiệt độ và Độ ẩm hợp lệ từ file để phân tích.")
                
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
