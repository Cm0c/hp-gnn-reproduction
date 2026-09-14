from build_timeline import load_build_timeline
def load_build_windows(data_dir):
    PRE_ICTAL  = 1800
    POST_ICTAL = 1800 
    windows = []
    window_counts = {'total': 0,'preictal': 0,'ictal': 0,'postictal':0,'interictal': 0,}
    timeline,seizures_time = load_build_timeline(data_dir)
    g_len = 5
    for rec in timeline:
        N = int(rec['duration']/g_len)
        for i in range(N):
            g_start = rec['start'] + i*g_len
            g_end = g_start + g_len
            mid = (g_start+g_end)/2
            best_state = 0
            best_priority = 0
            to_seizure = 90
            for idx,s in enumerate(seizures_time):
                to_seizure_num = 90
                if idx+1<len(seizures_time):
                    next_start = seizures_time[idx+1]['start']
                else:
                    next_start = float('inf')
                if mid>=s['start'] and mid<=s['end']:
                    cand_state, cand_pri = 2, 3
                    to_seizure_num = 0
                elif mid>s['end'] and mid<=s['end']+POST_ICTAL:
                    cand_state, cand_pri = 3, 2
                    to_seizure_num = (next_start-mid)/60
                elif mid<s['start'] and mid>=s['start']-PRE_ICTAL:
                    cand_state, cand_pri = 1, 1
                    to_seizure_num = (s['start'] - mid) / 60
                else: continue
                if cand_pri > best_priority:
                    best_state, best_priority = cand_state, cand_pri
                to_seizure = min(to_seizure,to_seizure_num)
            windows.append({'file':rec['file'],'g_start':g_start,'g_end':g_end,
                            'state':best_state,'to_seizure':to_seizure})
            window_counts['total']+=1
            match best_state:
                case 0: window_counts['interictal']+=1
                case 1:window_counts['preictal']+=1
                case 2:window_counts['ictal']+=1
                case 3:window_counts['postictal']+=1
    return windows,window_counts
if __name__=="__main__":
    windows,windows_counts = load_build_windows("data/raw/chbmit/chb01")
    print(f"窗口总数：{windows_counts['total']}")
    print(f"发作期：{windows_counts['ictal']}")
    print(f"发作后期：{windows_counts['postictal']}")
    print(f"发作前期：{windows_counts['preictal']}")
    print(f"正常：{windows_counts['interictal']}")
    ts = [w['to_seizure'] for w in windows]
    print(f"to_seizure范围：{min(ts)} ~ {max(ts)}")
