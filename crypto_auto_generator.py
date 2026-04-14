def download_source_video(video_url: str, cache_dir: str,
                           progress_callback=None,
                           cookies_file: str = "") -> tuple:
    """
    YouTube 영상을 전체 다운로드 (캐시). 여러 yt-dlp client 순차 시도.
    Streamlit Cloud 봇 차단 회피용 다중 fallback + 쿠키 지원.
    cookies_file: Netscape 형식 쿠키 파일 경로 (Chrome 확장 'Get cookies.txt LOCALLY'로 export)
    반환: (local_path, error_msg)
    """
    import yt_dlp
    os.makedirs(cache_dir, exist_ok=True)
    vid_id = _get_youtube_video_id(video_url) or "video"
    cache_path = os.path.join(cache_dir, f"source_{vid_id}.mp4")
 
    # 이미 다운로드된 경우
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100000:
        return cache_path, ""
 
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0.0.0 Safari/537.36")
 
    # 쿠키가 있으면 web client 우선 (쿠키 효과적), 없으면 mobile 우선
    has_cookies = bool(cookies_file and os.path.exists(cookies_file))
    # format 전략: 점점 더 관대하게 fallback
    # 'bv*+ba/b' = bestvideo+bestaudio → merge, 실패시 단일 best
    # 마지막은 그냥 'best' (어떤 포맷이든)
    if has_cookies:
        client_strategies = [
            # (client, format, use_cookies)
            (['web'],         'bv*[height<=720]+ba/b[height<=720]/bv*+ba/best',  True),
            (['web'],         'best',                                             True),
            (['mweb'],        'bv*[height<=480]+ba/b[height<=480]/best',          True),
            (['tv_embedded'], 'best',                                             True),
            (['android'],     'best',                                             True),
            (['ios'],         'best',                                             True),
            # 쿠키 빼고 시도 (일부 영상은 쿠키 없이가 더 잘됨)
            (['android'],     'best',                                             False),
            (['ios'],         'best',                                             False),
            (['tv_embedded'], 'best',                                             False),
        ]
    else:
        client_strategies = [
            (['android'],     'best[height<=720]/best',  False),
            (['ios'],         'best',                     False),
            (['tv_embedded'], 'best',                     False),
            (['web_embedded'],'best',                     False),
            (['mweb'],        'best',                     False),
            (['web'],         'best',                     False),
        ]
 
    errors = []
    for i, strategy in enumerate(client_strategies):
        client, fmt, use_this_cookies = strategy
        actual_cookies = has_cookies and use_this_cookies
        if progress_callback:
            cookie_tag = " +🍪" if actual_cookies else ""
            progress_callback(f"다운로드 시도 {i+1}/{len(client_strategies)} (client={client[0]}{cookie_tag}, fmt={fmt[:30]})")
        try:
            ydl_opts = {
                'format': fmt,
                'outtmpl': cache_path,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 2,
                'fragment_retries': 2,
                'http_headers': {'User-Agent': ua},
                'extractor_args': {'youtube': {'player_client': client}},
                'merge_output_format': 'mp4',
                'ignoreerrors': False,
            }
            if actual_cookies:
                ydl_opts['cookiefile'] = cookies_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100000:
                return cache_path, ""
        except Exception as e:
            err_msg = str(e)[:150]
            errors.append(f"{client[0]}{'(쿠키)' if actual_cookies else ''}: {err_msg}")
            # 실패한 부분 파일 제거
            for ext in [".mp4", ".webm", ".mkv", ".part", ".m4a"]:
                p = cache_path.replace(".mp4", ext)
                if os.path.exists(p) and os.path.getsize(p) < 100000:
                    try: os.remove(p)
                    except: pass
            continue
 
    # 마지막 수단: 모든 조건 제거하고 default 설정으로 시도
    try:
        if progress_callback:
            progress_callback(f"최종 시도 ({len(client_strategies)+1}/...): yt-dlp default settings")
        ydl_opts_fallback = {
            'format': 'best',
            'outtmpl': cache_path,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 60,
            'http_headers': {'User-Agent': ua},
        }
        if has_cookies:
            ydl_opts_fallback['cookiefile'] = cookies_file
        with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
            ydl.download([video_url])
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100000:
            return cache_path, ""
    except Exception as e:
        errors.append(f"default: {str(e)[:150]}")
 
    hint = ""
    if not has_cookies:
        hint = "\n\n💡 **해결책**: 쿠키 업로드 (⚡ 원본 영상 업로드 섹션 → 🍪 YouTube 쿠키 탭)"
    else:
        hint = ("\n\n💡 **쿠키가 만료되었을 수 있어요.** YouTube에 다시 로그인 후 "
                "쿠키를 재export해서 Streamlit Secrets의 `youtube_cookies` 값을 교체해보세요.")
    return "", "모든 client 실패:\n" + "\n".join(errors[:5]) + hint
 
