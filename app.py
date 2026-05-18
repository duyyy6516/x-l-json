import streamlit as st
import pandas as pd
import numpy as np
import json

# Cấu hình giao diện ứng dụng tối giản
st.set_page_config(
    page_title="Công Cụ Tính & Phân Loại VPD Nhà Kính",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Công Cụ Tính & Phân Loại VPD Nhà Kính")
st.markdown("Ứng dụng tự động quy đổi dữ liệu thô, tính toán chỉ số **VPD** và tạo cột phân loại trạng thái môi trường.")

def calculate_vpd(temp, humi):
    """Tính toán chỉ số VPD (kPa) từ Nhiệt độ và Độ ẩm theo công thức Tetens"""
    vp_sat = 0.61078 * np.exp((17.27 * temp) / (temp + 237.3))
    vpd = vp_sat * (1 - (humi / 100))
    return np.clip(vpd, 0, None)

def classify_vpd_case(vpd, humi):
    """Dựa vào giá trị VPD và độ ẩm đã tính để lọc ra Trường hợp (TH) cụ thể"""
    if humi >= 99.5 or vpd == 0:
        return "TH5: Bão hòa hơi nước (Ẩm bão hòa)"
    elif vpd < 0.4:
        return "TH1: VPD Quá Thấp (Không khí quá ẩm)"
    elif 0.4 <= vpd < 0.8:
        return "TH2: Thấp Tối Ưu (Ẩm dịu mát cho cây con)"
    elif 0.8 <= vpd <= 1.2:
        return "TH3: Cao Tối Ưu (Vùng quang hợp mạnh tốt nhất)"
    else:
        return "TH4: VPD Quá Cao (Stress khô nóng/Hanh khô)"

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
            
            # Danh sách chứa các bảng dữ liệu sau khi xử lý của từng trạm
            processed_chunks = []
            
            # Duyệt qua từng Trạm có trong file để xử lý cột Nhiệt độ và Độ ẩm tương ứng
            for station_id in df[stt_col].unique():
                sub_df = df[df[stt_col] == station_id].copy()
                
                t_col, h_col = None, None
                
                if station_id == "5":
                    # Trạm 5 không khí: Lấy tempKK và humiKK
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
                
                # Nếu trạm có đủ cặp Nhiệt độ và Độ ẩm thì tiến hành tính toán
                if t_col and h_col:
                    sub_df = sub_df.dropna(subset=[t_col, h_col])
                    if not sub_df.empty:
                        # 1. Tính chỉ số VPD trước
                        sub_df['VPD (kPa)'] = calculate_vpd(sub_df[t_col], sub_df[h_col]).round(3)
                        
                        # 2. Dựa vào VPD lọc ra Trường hợp và tạo thêm cột ghi nhận điều đó
                        sub_df['Phân Loại Trạng Thái'] = sub_df.apply(lambda row: classify_vpd_case(row['VPD (kPa)'], row[h_col]), axis=1)
                        
                        # Chỉ lấy đúng các cột cần in ra màn hình
                        processed_chunks.append(sub_df[[time_col, stt_col, 'VPD (kPa)', 'Phân Loại Trạng Thái']])
            
            # Gộp chung dữ liệu các trạm lại và in ra bảng tổng hợp
            if processed_chunks:
                final_df = pd.concat(processed_chunks, ignore_index=True)
                # Sắp xếp thứ tự xuôi theo dòng thời gian
                final_df = final_df.sort_values(by=time_col, ascending=True)
                
                st.subheader("📋 Bảng Kết Quả Chỉ Số VPD & Phân Loại Trường Hợp Tổng Hợp")
                st.write(f"Tổng số mốc xử lý thành công: **{len(final_df)}** dòng.")
                
                # In ra giao diện bảng sạch theo yêu cầu
                st.dataframe(final_df, use_container_width=True)
            else:
                st.warning("⚠️ Không thể trích xuất dữ liệu Nhiệt độ và Độ ẩm hợp lệ từ file để phân tích.")
                
    except Exception as e:
        st.error(f"Không thể đọc file JSON. Lỗi hệ thống: {str(e)}")
