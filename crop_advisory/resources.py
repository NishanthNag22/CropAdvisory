"""Optional sampled process memory and CPU-package energy measurements.

RSS is the sampled sum across requested process trees, not unique physical RAM.
Ollama must be included explicitly for inference-server memory measurements.
"""
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path


def read_rapl():
    readings={}
    root=Path('/sys/class/powercap')
    for path in root.glob('intel-rapl:*/energy_uj'):
        if not re.fullmatch(r'intel-rapl:\d+',path.parent.name):continue
        try:
            readings[str(path)]={'energy_uj':int(path.read_text()),'range_uj':int((path.parent/'max_energy_range_uj').read_text())}
        except (OSError,ValueError):continue
    return readings


def energy_delta(before, after):
    common=set(before)&set(after)
    if not common:return None
    total=0
    for key in common:
        diff=after[key]['energy_uj']-before[key]['energy_uj']
        if diff<0:diff+=before[key]['range_uj']
        total+=diff/1e6
    return total


class ResourceMonitor:
    def __init__(self,pids=None,interval=.05):
        self.pids=set(pids or [os.getpid()]);self.pids.add(os.getpid())
        self.interval=interval;self.stop=threading.Event();self.peak=None;self.gpu_peak=None;self.samples=0;self.errors=[]
        self.psutil=None
        self.thread=None
    def sample(self):
        if self.psutil is None:return
        processes={}
        for pid in self.pids:
            try:
                proc=self.psutil.Process(pid)
                for p in [proc]+proc.children(recursive=True):processes[p.pid]=p
            except self.psutil.Error as exc:self.errors.append(type(exc).__name__)
        rss=0
        for p in processes.values():
            try:rss+=p.memory_info().rss
            except self.psutil.Error:continue
        self.peak=max(self.peak or 0,rss);self.samples+=1
        if shutil.which('nvidia-smi') and self.samples%10==1:
            try:
                raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=2)
                values=[]
                for line in raw.splitlines():
                    pid,value=(part.strip() for part in line.split(',',1))
                    if int(pid) in processes:values.append(float(value)*1024*1024)
                if values:self.gpu_peak=max(self.gpu_peak or 0,sum(values))
            except (OSError,ValueError,subprocess.SubprocessError):pass
    def loop(self):
        while not self.stop.wait(self.interval):self.sample()
    def __enter__(self):
        try:
            import psutil
            self.psutil=psutil
        except ImportError:self.errors.append('Install psutil for sampled process memory.')
        self.before=read_rapl();self.sample()
        if self.psutil is not None:
            self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
        return self
    def __exit__(self,*args):
        self.stop.set()
        if self.thread:self.thread.join(timeout=3)
        self.sample();self.after=read_rapl()
    def report(self):
        return {'sampled_peak_process_tree_rss_bytes':self.peak,'sampled_peak_gpu_bytes':self.gpu_peak,'samples':self.samples,
            'monitor_pids':sorted(self.pids),'interval_seconds':self.interval,'cpu_package_energy_joules':energy_delta(self.before,self.after),
            'errors':sorted(set(self.errors)), 'scope':'Client plus explicitly requested process trees. Shared pages may be counted more than once. RAPL is system CPU-package energy, not inference-only energy. GPU sampling requires NVIDIA tooling.'}
