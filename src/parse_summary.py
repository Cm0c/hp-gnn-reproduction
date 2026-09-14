import os
def load_summary(data_dir):
    file_names = []
    seizures   = []
    current_file = None
    with open(os.path.join(data_dir, "chb01-summary.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "Number of Seizures in File: 0":
                file_names.append(current_file)
                continue
            if line.startswith("File Name:"):
                current_file = line.split(':',1)[1].strip()
            elif line.startswith("Seizure Start Time:"):
                start = float(line.split(":", 1)[1].strip().split()[0])
            elif line.startswith("Seizure End Time:"):
                end = float(line.split(":",1)[1].strip().split()[0])
                file_names.append(current_file)
                seizures.append({'file':current_file,'start':start,'end':end})
                start = end = None
    return file_names,seizures
if __name__=="__main__":
    DATA_DIR = "data/raw/chbmit/chb01"
    file_names, seizures = load_summary(DATA_DIR)
    disk_files = os.listdir(DATA_DIR)
    by_file = {s['file']: s for s in seizures}
    alledf = 0
    seedf = 0
    qsedf = 0
    for rec in file_names:
        alledf+=1
        if rec in disk_files:
            print(f"{rec} 下了")
            if rec in by_file:
                s = by_file[rec]
                print(f"  发作 {s['start']}~{s['end']}")
                seedf+=1
        else:
            print(f"{rec} 没下")
            qsedf+=1
    print("文件名总数: ",alledf)
    print("发作次数: ",seedf)
    print("缺失文件: ",qsedf)