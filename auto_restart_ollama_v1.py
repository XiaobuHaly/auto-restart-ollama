import subprocess
import re
import time
import sys

# 配置参数
COMMAND = ['ollama', 'run', 'deepseek-r1:1.5b']
SPEED_THRESHOLD = 1.0  # MB/s
CHECK_INTERVAL = 1    # 速度检查间隔（秒）
MIN_RUN_TIME = 40      # 最小运行时间（秒）

def parse_speed(line):
    """解析下载速度（返回MB/s单位）"""
    match = re.search(r'(\d+\.?\d*)\s+(KB/s|MB/s|GB/s)', line)
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
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None

def terminate_process(process):
    """跨平台终止进程"""
    if sys.platform == 'win32':
        subprocess.run(f'taskkill /F /T /PID {process.pid}', shell=True)
    else:
        process.terminate()

def main():
    while True:
        print("\n启动下载进程...")
        start_time = time.time()
        process = subprocess.Popen(
            COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8'
        )

        try:
            for line in iter(process.stdout.readline, ''):
                # 实时输出内容
                print(line, end='', flush=True)
                
                # 检查下载进度
                if (progress := parse_progress(line)) is not None:
                    if progress >= 100:
                        print("\n下载已完成！")
                        return
                
                # 检查速度
                if (time.time() - start_time > MIN_RUN_TIME and 
                    (speed := parse_speed(line)) is not None):
                    print(f"\n当前速度: {speed:.2f} MB/s")
                    
                    if speed < SPEED_THRESHOLD:
                        print(f"速度低于阈值 {SPEED_THRESHOLD} MB/s，准备重启...")
                        terminate_process(process)
                        time.sleep(2)
                        break

            # 等待进程结束
            process.wait()
            if process.returncode == 0:
                print("下载成功完成！")
                return
                
        except KeyboardInterrupt:
            print("\n用户中断，退出程序")
            terminate_process(process)
            return
            
        except Exception as e:
            print(f"发生错误: {str(e)}")
            terminate_process(process)
        
        print("等待5秒后重试...")
        time.sleep(5)

if __name__ == "__main__":
    main()