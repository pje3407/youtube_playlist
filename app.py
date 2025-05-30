import streamlit as st
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from collections import defaultdict

# 페이지 기본 설정
st.set_page_config(
    page_title="Youtube Playlist Curation",
    page_icon="🎵",
    layout="wide"
)

# YouTube API 설정
def get_youtube_client():
    try:
        api_key = st.secrets["YOUTUBE_API_KEY"]
        if not api_key:
            st.error("YouTube API 키가 설정되지 않았습니다")
            return None
        return build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        st.error(f"YouTube API 키 설정 오류: {str(e)}")
        return None

# Gemini API 설정
def configure_genai():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        if not api_key:
            st.error("API 키가 설정되지 않았습니다")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"API 키 설정 오류: {str(e)}")
        return False

# 테마별 키워드 생성 함수
def generate_keywords(theme):
    # 기본 키워드 사전
    keyword_dict = {
        '비': ['빗소리', '슬픔', '우울', '감성', '새벽'],
        '비 오는 날': ['빗소리', '감성', '우울', '새벽', '차분한'],
        '맑은 날': ['상쾌한', '청량한', '산뜻한', '햇살', '드라이브'],
        '운동': ['신나는', '에너지', '파워풀', '힙합', '댄스'],
        '운동할 때': ['신나는', '에너지', '파워풀', '힙합', '댄스'],
        '공부': ['로파이', '집중', '차분한', '재즈', '피아노'],
        '공부할 때': ['로파이', '집중', '차분한', '재즈', '피아노'],
        '밤': ['새벽감성', '감성', '몽환적인', '재즈', '어쿠스틱'],
        '밤에': ['새벽감성', '감성', '몽환적인', '재즈', '어쿠스틱'],
        '샤워': ['신나는', '팝송', '노래방', '즐거운', '발라드'],
        '샤워할 때': ['신나는', '팝송', '노래방', '즐거운', '발라드'],
        '요리': ['경쾌한', '즐거운', '쿠킹', '재즈', '팝송'],
        '요리할 때': ['경쾌한', '즐거운', '쿠킹', '재즈', '팝송'],
        '산책': ['여유로운', '따뜻한', '편안한', '어쿠스틱', '잔잔한'],
        '산책할 때': ['여유로운', '따뜻한', '편안한', '어쿠스틱', '잔잔한'],
        '일': ['차분한', '집중', '모던한', '재즈', '로파이'],
        '일할 때': ['차분한', '집중', '모던한', '재즈', '로파이'],
        '휴식': ['편안한', '힐링', '잔잔한', '어쿠스틱', '피아노'],
        '휴식할 때': ['편안한', '힐링', '잔잔한', '어쿠스틱', '피아노'],
        '슬픔': ['감성', '이별', '슬픈', '발라드', '새벽감성'],
        '우울': ['감성', '위로', '슬픔', '발라드', '새벽감성'],
        '행복': ['신나는', '즐거운', '행복한', '팝송', '밝은'],
        '설렘': ['로맨틱', '두근두근', '사랑', '달달한', '설레는'],
        '사랑': ['로맨틱', '달달한', '설렘', '고백', '사랑노래'],
        '이별': ['이별노래', '슬픔', '그리움', '발라드', '새벽감성']
    }
    
    # 입력된 테마에서 핵심 키워드 추출
    clean_theme = theme.replace('할 때', '').replace('에서', '').replace('에', '').replace('을', '').replace('를', '').replace('듣기 좋은', '').replace('노래', '').strip()
    
    # 기본 키워드가 있는 경우
    if clean_theme in keyword_dict:
        return keyword_dict[clean_theme]
    
    # 입력된 문장에서 키워드 찾기
    for key in keyword_dict.keys():
        if key in clean_theme:
            return keyword_dict[key]
    
    # 기본 키워드가 없는 경우, 일반적인 분위기 키워드 반환
    return ['신나는', '감성적인', '차분한', '즐거운', '편안한']

# YouTube 비디오 검색
def search_youtube_videos(keyword, max_results=5, exclude_ids=None):
    youtube = get_youtube_client()
    if not youtube:
        st.error("YouTube API 클라이언트 생성 실패")
        return []
    
    try:
        search_response = youtube.search().list(
            q=f"playlist 음악 {keyword}",
            part='snippet',
            maxResults=max_results * 4,  # 더 많은 결과를 가져와서 필터링
            type='video',
            videoEmbeddable='true',
            videoDuration='medium'
        ).execute()
        
        videos = []
        exclude_ids = set(exclude_ids or [])  # None인 경우 빈 set으로 초기화
        
        for item in search_response.get('items', []):
            if len(videos) >= max_results:
                break
                
            video_id = item['id']['videoId']
            # 이미 표시된 비디오는 제외
            if video_id in exclude_ids:
                continue
                
            title = item['snippet']['title'].lower()
            if ('playlist' in title or 
                '플레이리스트' in title or 
                'mix' in title or 
                '모음' in title or 
                '노래 모음' in title):
                video_data = {
                    'id': video_id,
                    'title': item['snippet']['title'],
                    'channel': item['snippet']['channelTitle'],
                    'embed_url': f"https://www.youtube.com/embed/{video_id}",
                    'keyword': keyword
                }
                videos.append(video_data)
        
        # 플레이리스트 영상이 부족한 경우 일반 영상으로 채움
        if len(videos) < max_results:
            for item in search_response.get('items', []):
                if len(videos) >= max_results:
                    break
                    
                video_id = item['id']['videoId']
                if video_id not in exclude_ids and not any(v['id'] == video_id for v in videos):
                    video_data = {
                        'id': video_id,
                        'title': item['snippet']['title'],
                        'channel': item['snippet']['channelTitle'],
                        'embed_url': f"https://www.youtube.com/embed/{video_id}",
                        'keyword': keyword
                    }
                    videos.append(video_data)
        
        return videos
    except HttpError as e:
        st.error(f"YouTube API 오류: {str(e)}")
        return []
    except Exception as e:
        st.error(f"예상치 못한 오류 발생: {str(e)}")
        return []

# 테마 분류 함수
def classify_theme(user_input):
    # 입력에서 조사 제거
    clean_input = user_input.replace('할 때', '').replace('에서', '').replace('에', '').replace('을', '').replace('를', '').strip()
    return clean_input

# 사이드바 UI
def render_sidebar():
    with st.sidebar:
        # 홈 버튼 추가
        st.markdown('<div class="sidebar-home">', unsafe_allow_html=True)
        if st.button("🏠 홈으로 돌아가기"):
            st.session_state.selected_playlist_keyword = None
            st.session_state.selected_keyword = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("## 📂 저장한 테마")
        
        # 좋아요 누른 비디오만 키워드별로 그룹화
        playlists = defaultdict(list)
        for video in st.session_state.liked_videos.values():
            playlists[video['keyword']].append(video)
        
        if not playlists:
            st.info("아직 저장된 음악이 없습니다.")
            return
        
        for keyword, videos in playlists.items():
            if st.button(f"🎵 {keyword} ({len(videos)})", key=f"playlist_{keyword}"):
                st.session_state.selected_playlist_keyword = keyword
                st.rerun()

# 저장된 플레이리스트 표시
def show_saved_playlist():
    if not st.session_state.selected_playlist_keyword:
        return
    
    keyword = st.session_state.selected_playlist_keyword
    videos = [v for v in st.session_state.liked_videos.values() if v['keyword'] == keyword]
    
    if not videos:
        st.info(f"'{keyword}' 키워드로 저장된 음악이 없습니다.")
        return
    
    st.markdown(f"## 🎵 {keyword} 플레이리스트")
    
    st.markdown('<div class="video-grid">', unsafe_allow_html=True)
    for video in videos:
        st.markdown(f"""
        <div class="video-card">
            <div class="iframe-container">
                <iframe
                    src="{video['embed_url']}"
                    title="{video['title']}"
                    frameborder="0"
                    allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen>
                </iframe>
            </div>
            <div class="video-info">
                <div class="video-title">{video['title']}</div>
                <div class="channel-name">{video['channel']}</div>
            </div>
            <div class="action-buttons">
                <button class="delete-button" onclick="handleDelete('{video['id']}')" id="delete_{video['id']}">
                    ❌
                </button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button('❌', key=f"delete_{video['id']}"):
            del st.session_state.liked_videos[video['id']]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# 세션 상태 초기화
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'selected_keyword' not in st.session_state:
    st.session_state.selected_keyword = None
if 'liked_videos' not in st.session_state:
    st.session_state.liked_videos = {}
if 'current_videos' not in st.session_state:
    st.session_state.current_videos = []
if 'selected_playlist_keyword' not in st.session_state:
    st.session_state.selected_playlist_keyword = None
if 'current_theme' not in st.session_state:
    st.session_state.current_theme = None
if 'current_keywords' not in st.session_state:
    st.session_state.current_keywords = []
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0

# Custom CSS 스타일
st.markdown("""
    <style>
        /* 전체 배경 설정 */
        .stApp {
            background: linear-gradient(135deg, #000000, #800000) !important;
        }
        
        /* 제목 스타일 */
        .title-text {
            font-size: 3.5rem !important;
            font-weight: 700 !important;
            margin-bottom: 1rem !important;
            color: #ffffff !important;
            text-shadow: 2px 2px 4px rgba(255, 0, 0, 0.3);
        }
        
        .subtitle-text {
            font-size: 1rem !important;
            color: #ff9999 !important;
            font-weight: 500 !important;
            margin-bottom: 2rem !important;
            opacity: 0.9;
        }
        
        /* 입력 라벨 스타일 */
        .stTextInput label {
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 1.2rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* 입력 필드와 버튼 컨테이너 */
        .search-container {
            display: flex !important;
            align-items: center !important;
            gap: 1rem !important;
            margin-bottom: 2rem !important;
        }
        
        /* 입력 필드 스타일 */
        .stTextInput > div > div {
            background-color: rgba(0, 0, 0, 0.3) !important;
            border: 1px solid rgba(255, 0, 0, 0.2) !important;
            border-radius: 8px !important;
            color: white !important;
            backdrop-filter: blur(5px);
        }
        
        /* 검색 버튼 스타일 수정 */
        .search-button .stButton > button {
            height: 46px !important;
            min-width: 80px !important;
            background: rgba(0, 0, 0, 0.7) !important;
            color: white !important;
            border: 2px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            font-size: 1.2rem !important;
            font-weight: 600 !important;
            margin-top: 25px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
            backdrop-filter: blur(5px) !important;
            padding: 0 1.5rem !important;
        }
        
        .search-button .stButton > button:hover {
            background: rgba(0, 0, 0, 0.8) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* 해시태그 컨테이너 수정 */
        .hashtag-container {
            display: inline-flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0.3rem !important;
            margin: 0.5rem 0 !important;
            padding: 0.3rem 0 !important;
            overflow-x: auto !important;
            align-items: center !important;
            justify-content: flex-start !important;
            width: 100% !important;
            white-space: nowrap !important;
        }
        
        .hashtag-container::-webkit-scrollbar {
            display: none !important;
        }
        
        /* 해시태그 버튼 컨테이너 */
        .hashtag-container > div {
            display: inline-block !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* 해시태그 버튼 수정 */
        .hashtag-container .stButton > button {
            background: transparent !important;
            color: rgba(255, 255, 255, 1) !important;
            border: 2px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 20px !important;
            padding: 0.3rem 0.8rem !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            margin: 0 !important;
            box-shadow: none !important;
            min-width: fit-content !important;
            white-space: nowrap !important;
            display: inline-block !important;
            line-height: 1.2 !important;
        }
        
        .hashtag-container .stButton > button:hover {
            background: rgba(255, 0, 0, 0.1) !important;
            border-color: #ff0000 !important;
            color: #ff0000 !important;
            transform: translateY(-2px) !important;
        }
        
        /* 선택된 키워드 스타일 */
        .selected-keyword .stButton > button {
            background: rgba(255, 0, 0, 0.1) !important;
            border-color: #ff0000 !important;
            color: #ff0000 !important;
        }
        
        /* 비디오 그리드 */
        .video-grid {
            display: flex !important;
            flex-direction: column !important;
            gap: 2rem !important;
            padding: 1rem 0 !important;
        }
        
        /* 비디오 카드 */
        .video-card {
            background: rgba(0, 0, 0, 0.4) !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            backdrop-filter: blur(5px) !important;
            transition: transform 0.3s ease !important;
        }
        
        .video-card:hover {
            transform: translateY(-5px) !important;
        }
        
        /* iframe 컨테이너 */
        .iframe-container {
            position: relative !important;
            width: 100% !important;
            padding-bottom: 56.25% !important;
            margin-bottom: 1rem !important;
        }
        
        .iframe-container iframe {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            border: none !important;
            border-radius: 8px !important;
        }
        
        /* 비디오 정보 */
        .video-info {
            margin-top: 1rem !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        
        .video-title {
            color: #ffffff !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
            margin-right: 1rem !important;
        }
        
        .channel-name {
            color: rgba(255, 255, 255, 0.7) !important;
            font-size: 0.9rem !important;
        }
        
        /* 좋아요 버튼 */
        .stButton > button {
            background: none !important;
            border: none !important;
            padding: 0.5rem !important;
            font-size: 1.2rem !important;
            line-height: 1 !important;
            cursor: pointer !important;
            transition: transform 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: scale(1.1) !important;
        }
        
        /* 사이드바 스타일 수정 */
        section[data-testid="stSidebar"] {
            background: rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px) !important;
        }
        
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        
        section[data-testid="stSidebar"] .stMarkdown {
            color: rgba(255, 255, 255, 0.8) !important;
        }
        
        section[data-testid="stSidebar"] h2 {
            color: white !important;
            font-weight: 600 !important;
        }
        
        section[data-testid="stSidebar"] .stButton > button {
            background: transparent !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            width: 100% !important;
            margin: 4px 0 !important;
            transition: all 0.3s ease !important;
        }
        
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255, 255, 255, 0.1) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
        }
        
        /* 테마 결과 */
        .theme-result {
            font-size: 1.5rem !important;
            font-weight: 500 !important;
            color: #ff4d4d !important;
            margin-top: 2rem !important;
            padding: 1rem !important;
            border-radius: 10px !important;
            background-color: rgba(255, 0, 0, 0.1) !important;
            backdrop-filter: blur(5px) !important;
        }
        
        /* 새로고침 버튼 */
        .refresh-button .stButton > button {
            background: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.9rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            height: auto !important;
            width: auto !important;
        }
        
        .refresh-button .stButton > button:hover {
            background: rgba(255, 0, 0, 0.2) !important;
            transform: translateY(-2px) !important;
        }
    </style>
""", unsafe_allow_html=True)

# 메인 UI 렌더링
render_sidebar()

# 제목과 설명
st.markdown('<p class="title-text">Youtube Playlist Curation</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">새로운 음악을 찾는 당신을 위한 감각적인 큐레이션.</p>', unsafe_allow_html=True)

# 구분선 추가
st.markdown("---")

# API 구성 확인
if not configure_genai():
    st.stop()

# 선택된 플레이리스트가 있으면 표시
if st.session_state.selected_playlist_keyword:
    show_saved_playlist()
else:
    # 검색 UI
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "어떤 상황이나 분위기의 음악을 찾으시나요?",
            value=st.session_state.user_input,
            placeholder="예: 샤워할 때, 운동할 때, 공부할 때",
            key="input_text"
        )
    
    with col2:
        st.markdown('<div class="search-button">', unsafe_allow_html=True)
        if st.button("검색", key="search_button"):
            if user_input:
                st.session_state.user_input = user_input
                theme = classify_theme(user_input)
                st.session_state.current_theme = theme
                st.session_state.current_keywords = generate_keywords(theme)[:5]
                st.session_state.refresh_counter = 0
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 현재 테마가 있으면 표시
    if st.session_state.current_theme:
        # 키워드를 한 줄에 표시
        st.markdown('<div class="hashtag-container">', unsafe_allow_html=True)
        for keyword in st.session_state.current_keywords[:5]:
            keyword_class = "selected-keyword" if st.session_state.get('selected_keyword') == keyword else ""
            st.markdown(f'<div class="{keyword_class}">', unsafe_allow_html=True)
            if st.button(f"#{keyword}", key=f"keyword_{keyword}_{st.session_state.refresh_counter}"):
                st.session_state.selected_keyword = keyword
                st.session_state.current_videos = search_youtube_videos(keyword)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# 선택된 키워드가 있으면 비디오 표시
if st.session_state.get('selected_keyword'):
    st.subheader(f"'{st.session_state.selected_keyword}' 관련 음악")
    
    # 새로고침 버튼
    if st.button("🔄 새로운 플레이리스트 검색", key=f"refresh_{st.session_state.refresh_counter}"):
        st.session_state.refresh_counter += 1
        current_video_ids = [v['id'] for v in st.session_state.current_videos] if st.session_state.current_videos else []
        new_videos = search_youtube_videos(
            st.session_state.selected_keyword,
            exclude_ids=current_video_ids
        )
        if new_videos:
            st.session_state.current_videos = new_videos
            st.rerun()
    
    # 비디오 목록 표시
    if not st.session_state.get('current_videos'):
        st.warning("검색된 영상이 없습니다.")
    else:
        st.markdown('<div class="video-grid">', unsafe_allow_html=True)
        for video in st.session_state.current_videos:
            is_liked = video['id'] in st.session_state.liked_videos
            like_button_key = f"like_{video['id']}_{st.session_state.refresh_counter}"
            
            st.markdown(f"""
            <div class="video-card">
                <div class="iframe-container">
                    <iframe
                        src="{video['embed_url']}"
                        title="{video['title']}"
                        frameborder="0"
                        allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen>
                    </iframe>
                </div>
                <div class="video-info">
                    <div>
                        <div class="video-title">{video['title']}</div>
                        <div class="channel-name">{video['channel']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 좋아요 버튼을 별도로 표시
            if st.button('❤️' if is_liked else '🤍', key=like_button_key):
                if is_liked:
                    del st.session_state.liked_videos[video['id']]
                else:
                    st.session_state.liked_videos[video['id']] = video
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
