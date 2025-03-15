import subprocess
import re
import time
import sys
import os

# 配置参数
COMMAND = ['ollama', 'run', 'deepseek-r1:7b']
SPEED_THRESHOLD = 1.0  # MB/s
MIN_RUN_TIME = 20      # 最短运行时间（秒）
START_MONITORING_SPEED = 0.1  # 开始监控的初始速度阈值（MB/s）
PROGRESS_TIMEOUT = 300  # 新增：进度无更新超时时间（秒）

# Windows系统启用ANSI转义支持
if sys.platform == 'win32':
    os.system('')

def parse_speed(line):
    """解析下载速度（返回MB/s单位）"""
    match = re.search(r'(\d+\.?\d*)\s*([KMG]B/s)', line)
    if not match:
        return None
    
    value, unit = match.groups()
    value = float(value)
    
    # 统一转换为MB/s
    conversion = {
        'KB/s': 1/1024,
        'MB/s': 1,
        'GB/s': 1024
    }
    return value * conversion.get(unit, 1)

def parse_progress(line):
    """解析下载进度百分比"""
    match = re.search(r'(\d+)%\s+▕', line)
    return int(match.group(1)) if match else None

def terminate_process(process):
    """跨平台终止进程"""
    if sys.platform == 'win32':
        subprocess.run(f'taskkill /F /T /PID {process.pid}', shell=True)
    else:
        process.terminate()

def main():
    while True:
        print("\n\033[1;36m启动下载进程...\033[0m")
        start_time = time.time()
        last_progress_time = time.time()
        process = subprocess.Popen(
            COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8'
        )

        try:
            manifest_count = 0
            monitoring_speed = False
            last_progress = 0

            while True:
                # 非阻塞读取输出
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break  # 进程已结束
                    time.sleep(0.1)
                    # 检查进度超时
                    if time.time() - last_progress_time > PROGRESS_TIMEOUT:
                        print(f"\n\033[1;31m超过{PROGRESS_TIMEOUT}秒无进度更新，准备重启...\033[0m")
                        terminate_process(process)
                        time.sleep(2)
                        break
                    continue

                # 保留原始输出格式
                sys.stdout.write(line)
                sys.stdout.flush()

                # 改进的manifest过滤逻辑
                if 'pulling manifest' in line:
                    manifest_count += 1
                    if manifest_count > 1:
                        # 清除重复的manifest提示
                        sys.stdout.write("\033[1A\033[2K")  # 上移一行并清除
                        continue
                else:
                    manifest_count = 0

                # 解析进度和速度
                current_progress = parse_progress(line)
                current_speed = parse_speed(line)

                # 更新进度时间戳
                if current_progress is not None and current_progress > last_progress:
                    last_progress = current_progress
                    last_progress_time = time.time()

                # 进度监控
                if current_progress is not None:
                    if current_progress >= 100:
                        print("\n\033[1;32m下载已完成！\033[0m")
                        return

                # 速度监控逻辑
                if current_speed is not None:
                    # 当速度超过初始阈值时开始监控
                    if not monitoring_speed and current_speed >= START_MONITORING_SPEED:
                        print(f"\n\033[1;33m开始速度监控（>{START_MONITORING_SPEED}MB/s）...\033[0m")
                        monitoring_speed = True

                    # 符合监控条件时检查速度
                    if monitoring_speed and (time.time() - start_time > MIN_RUN_TIME):
                        print(f"\033[2K\r当前速度: {current_speed:.2f} MB/s", end='')
                        if current_speed < SPEED_THRESHOLD:
                            print(f"\n\033[1;31m速度低于阈值 {SPEED_THRESHOLD} MB/s，准备重启...\033[0m")
                            terminate_process(process)
                            time.sleep(2)
                            break

            # 检查进程退出状态
            if process.poll() == 0:
                print("\n\033[1;32m下载成功完成！\033[0m")
                return
                
        except KeyboardInterrupt:
            print("\n\033[1;33m用户中断，退出程序\033[0m")
            terminate_process(process)
            return
            
        except Exception as e:
            print(f"\n\033[1;31m发生错误: {str(e)}\033[0m")
            terminate_process(process)
        
        print("\n\033[1;35m等待5秒后重试...\033[0m")
        time.sleep(5)

if __name__ == "__main__":
    main()