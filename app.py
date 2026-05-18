import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng tối giản
st.set_page_config(
    page_title="Công Cụ Tính & Phân Tích VPD Nhà Kính",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Công Cụ Tính & Phân Tích VPD Nhà Kính")
st.markdown("Ứng dụng tự động tính chỉ số **VPD**, tự động bắt bệnh tách riêng cột **Trạng Thái, Lý Do** và **Cách Giải Quyết** trực tiếp dựa trên số liệu thực tế.")

def calculate_vpd(temp, humi):
    """Tính toán chỉ số VPD (kPa) từ Nhiệt độ và Độ ẩm theo công thức Tetens"""
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)

def analyze_environment_details(vpd, temp, humi):
    """
    Hàm trung tâm phân tích tách bạch thành 3 nội dung: Trạng Thái, Lý Do, Cách Giải Quyết.
    Không dùng ký hiệu TH1, TH4, TH5.
    """
    # 1. Kiểm tra trường hợp mất tín hiệu hoặc lỗi cảm biến ẩm
    if humi == 0:
        return pd.Series([
            "Mất Tín Hiệu Cảm Biến",
            "Độ ẩm trả về bằng 0% (Cảm biến đang để ngoài không khí hoặc bị tuột dây).",
            "Kiểm tra lại giắc cắm đầu dò và đường truyền tín hiệu phần cứng."
        ])
    
    # 2. Kiểm tra trạng thái bão hòa ẩm hoàn toàn
    if humi >= 99.5 or vpd == 0:
        return pd.Series([
            "Bão Hòa Hơi Nước",
            f"Độ ẩm trong môi trường chạm trần tuyệt đối ({humi}%).",
            "Bật ngay quạt hút, quạt đối lưu để cưỡng bức thoát ẩm; ngừng tưới nước hoàn toàn."
        ])
    
    # 3. Kiểm tra trạng thái VPD Thấp (Không khí quá ẩm)
    if vpd < 0.4:
        return pd.Series([
            "VPD Quá Thấp",
            f"Độ ẩm môi trường quá cao ({humi}%) kết hợp nhiệt độ thấp làm nghẹn rễ cây.",
            "Bật quạt đối lưu điều hòa không khí và mở bớt cửa thông gió hông nhà kính."
        ])
    
    # 4. Kiểm tra trạng thái Thấp Tối Ưu
    if 0.4 <= vpd < 0.8:
        return pd.Series([
            "Tối Ưu (Ẩm Dịu Mát)",
            "Nhiệt độ và Độ ẩm nằm trong dải điều hòa an toàn tuyệt đối.",
            "Môi trường hoàn hảo cho rễ non và cây con. Duy trì ổn định hệ thống."
        ])
    
    # 5. Kiểm tra trạng thái Cao Tối Ưu
    if 0.8 <= vpd <= 1.2:
        return pd.Series([
            "Tối Ưu (Quang Hợp Mạnh)",
            "Sự cân bằng tuyệt vời giúp khí khổng mở tối đa để hấp thụ dinh dưỡng.",
            "Môi trường kích năng suất tốt nhất cho cây trưởng thành. Duy trì vận hành."
        ])
    
    # 6. Kiểm tra trạng thái VPD Quá Cao (Phần lớn dữ liệu trong file của bạn)
    # Tự động bắt mạch lý do sâu hơn dựa trên thông số Nhiệt độ và Độ ẩm thật
    if temp > 40.0 and humi < 40.0:
        return pd.Series([
            "VPD Quá Cao",
            f"Nhiệt độ quá nóng ({temp}°C) đồng thời không khí quá khô cằn ({humi}%).",
            "Kéo lưới lan cắt nắng giảm bức xạ nhiệt trực tiếp và bật phun sương bù ẩm khẩn cấp."
        ])
    elif humi < 40.0:
        return pd.Series([
            "VPD Quá Cao",
            f"Độ ẩm môi trường sụt giảm sâu ({humi}%), không khí hanh khô gây mất nước bốc hơi nhanh.",
            "Kích hoạt hệ thống phun sương để tăng ẩm không khí lên dải an toàn."
        ])
    else:
        return pd.Series([
            "VPD Quá Cao",
            f"Nhiệt độ tăng cao ({temp}°C) hun đúc làm đẩy áp suất bốc hơi lên ngưỡng stress.",
            "Tăng cường chu kỳ tưới nhỏ giọt dưới gốc để cấp đủ nước cho bộ rễ làm mát cây."
        ])

# Khu vực tải file dữ liệu JSON
uploaded_file = st.file_uploader("Kéo thả file dữ liệu JSON vào đây để phân tích", type=["json"])

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
                        
                        # Bước 2: Phân tích sâu tách thành 3 nội dung cột riêng biệt dựa trên thông số thật
                        sub_df[['Trạng Thái', 'Lý Do Chi Tiết', 'Cách Giải Quyết']] = sub_df.apply(
                            lambda row: analyze_environment_details(row['VPD (kPa)'], row[t_col], row[h_col]), axis=1
                        )
                        
                        # Giữ lại các cột theo cấu trúc bảng sạch tinh gọn
                        sub_cols = [time_col, stt_col, 'VPD (kPa)', 'Trạng Thái', 'Lý Do Chi Tiết', 'Cách Giải Quyết']
                        processed_chunks.append(sub_df[sub_cols])
            
            # Gộp chung dữ liệu các trạm và xuất ra bảng tổng hợp duy nhất
            if processed_chunks:
                final_df = pd.concat(processed_chunks, ignore_index=True)
                final_df = final_df.sort_values(by=time_col, ascending=True)
                
                st.subheader("📋 Bảng Kết Quả Tính Toán Chỉ Số VPD & Hướng Dẫn Điều Hành Nhà Kính")
                st.write(f"Tổng số mốc thời gian xử lý thành công: **{len(final_df)}** dòng.")
                
                # Hiển thị bảng sạch cấu trúc phân tách rõ ràng ra giao diện
                st.dataframe(final_df, use_container_width=True)
            else:
                st.warning("⚠️ Không thể trích xuất dữ liệu Nhiệt độ và Độ ẩm hợp lệ từ file để phân tích.")
                
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
