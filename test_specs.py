
import platform
import psutil  # type: ignore[import-not-found]
import sys

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20 MB'
        1253656678 => '1.17 GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def print_system_specs():
    print(f"System: {platform.system()}")
    print(f"Node Name: {platform.node()}")
    print(f"Release: {platform.release()}")
    print(f"Version: {platform.version()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    
    # CPU
    print(f"Physical cores: {psutil.cpu_count(logical=False)}")
    print(f"Total cores: {psutil.cpu_count(logical=True)}")
    # CPU Frequencies
    cpufreq = psutil.cpu_freq()
    if cpufreq:
        print(f"Max Frequency: {cpufreq.max:.2f}Mhz")
        print(f"Current Frequency: {cpufreq.current:.2f}Mhz")
    
    # Memory
    svmem = psutil.virtual_memory()
    print(f"Total Memory: {get_size(svmem.total)}")
    print(f"Available Memory: {get_size(svmem.available)}")
    
    # Disk
    # partitions = psutil.disk_partitions()
    # for partition in partitions:
    #     print(f"Device: {partition.device}")
    #     try:
    #         partition_usage = psutil.disk_usage(partition.mountpoint)
    #         print(f"  Total: {get_size(partition_usage.total)}")
    #         print(f"  Free:  {get_size(partition_usage.free)}")
    #     except PermissionError:
    #         continue

if __name__ == "__main__":
    print_system_specs()
