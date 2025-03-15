import os
import subprocess
import re
import time

def parse_output(line):
    # 提取下载速度
    speed_match = re.search(r'([\d\.]+)\s*(KB|MB|GB)/s', line)
    if speed_match:
        speed = float(speed_match.group(1))
        unit = speed_match.group(2)
        if unit == 'GB':
            speed *= 1024 * 1024  # GB转换为KB
        elif unit == 'MB':
            speed *= 1024  # MB转换为KB
        # 速度统一为KB/s
    else:
        speed = None
    
    # 提取下载进度百分比
    progress_match = re.search(r'(\d+)%', line)
    if progress_match:
        progress = int(progress_match.group(1))
    else:
        progress = None
    
    # 提取已下载和总大小
    size_match = re.search(r'([\d\.]+\s*(KB|MB|GB))/([\d\.]+\s*(KB|MB|GB))', line)
    if size_match:
        downloaded = size_match.group(1)
        total_size = size_match.group(3)
    else:
        downloaded = None
        total_size = None
    
    # 提取剩余时间
    time_match = re.search(r'(\d+[smh])$', line.strip())
    if time_match:
        remaining_time = time_match.group(1)
    else:
        remaining_time = None
    
    return speed, progress, downloaded, total_size, remaining_time

def monitor_download(command, speed_threshold):
    # 添加ollama的安装路径到环境变量PATH
    ollama_path = r"C:\Users\48105\AppData\Local\Programs\Ollama"
    os.environ['PATH'] = ollama_path + os.pathsep + os.environ['PATH']

    while True:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore'
        )

        # 初始等待时间
        initial_wait_time = 40  # 等待10秒，让速度稳定
        print(f"⏳ 等待 {initial_wait_time} 秒，让下载速度稳定...")
        time.sleep(initial_wait_time)

        while True:
            line = process.stdout.readline()
            if not line:
                break

            # 处理回车符
            if '\r' in line:
                lines = line.split('\r')
                # 取最后一条信息
                current_line = lines[-1].strip()
            else:
                current_line = line.strip()

            # 清除当前行，打印新内容
            print('\r' + ' ' * 80, end='')  # 清空当前行
            print('\r' + current_line, end='')

            # 解析输出信息
            speed, progress, downloaded, total_size, remaining_time = parse_output(current_line)

            # 实时显示下载信息
            if progress is not None:
                status = f"🚀 进度: {progress}%"
                if downloaded and total_size:
                    status += f" | 大小: {downloaded}/{total_size}"
                if speed is not None:
                    status += f" | 速度: {speed:.2f} KB/s"
                if remaining_time:
                    status += f" | 剩余时间: {remaining_time}"
                print('\r' + ' ' * 80, end='')  # 清空当前行
                print('\r' + status, end='')

            # 检查速度是否低于阈值
            if speed is not None and speed < speed_threshold:
                print(f"\n⚠️ 检测到速度降至 {speed:.2f} KB/s，低于阈值，重启下载...")
                process.terminate()
                time.sleep(1)  # 等待1秒再重启
                break
        else:
            print("\n🎉 下载完成！")
            return 

if __name__ == "__main__":
    command = ["ollama", "pull", "deepseek-r1:7b"]
    speed_threshold = 500  # 设置你的速度阈值，单位KB/s
    monitor_download(command, speed_threshold)
