import mne
import os
from parse_summary import load_summary
def load_build_timeline(data_dir):
    timeline = []
    seizures_time = []
    file_names,seizures = load_summary(data_dir)
    edf_names = [name for name in os.listdir(data_dir) if name.endswith('.edf')]
    edf_names.sort()
    start = 0.0
    end = 0.0
    for rec in edf_names:
        raw = mne.io.read_raw_edf(os.path.join(data_dir, rec),preload=False,verbose='ERROR')
        sfreq=raw.info['sfreq']
        duration = raw.n_times/sfreq
        end+=duration
        timeline.append({'file':rec,'duration':duration,'start':start,'end':end})
        start+=duration
    by_file = {s['file']: s for s in seizures}
    for rec in timeline:
        if rec['file'] in by_file:
            s = by_file[rec['file']]
            seizures_time.append({'file':rec['file'],'start':rec['start']+s['start'],'end':rec['start']+s['end']})
    return timeline,seizures_time
if __name__=="__main__":
    timeline,seizures_time = load_build_timeline("data/raw/chbmit/chb01")
    by_file = {s['file']: s for s in seizures_time}
    print(f"{'file':<20}{'duration':>12}{'start':>12}{'end':>12}")
    for rec in timeline:
        print(f"{rec['file']:<20}{rec['duration']:>12}{rec['start']:>12}{rec['end']:>12}")
    print(f"{'seizure_file':<20}{'start':>12}{'end':>12}")
    for rec in timeline:
        if rec['file'] in by_file:
            s = by_file[rec['file']]
            print(f"{s['file']:<20}{s['start']:>12}{s['end']:>12}")
    print(f"总时长：{timeline[-1]['end']}")