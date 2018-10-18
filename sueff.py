#!/usr/bin/env python3
import subprocess
import sys

# usage:
# ./sueff.py [user]
# displays all active users if no user specified

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def cmd(s):
    return subprocess.check_output(s,shell=True).decode()

def get_active_users():
    return cmd(
        "squeue -h --state='R' -o %u | sort -u | tr '\n' ' '"
    ).split(' ')[:-1]

def get_user_id(user):
    return int(cmd("id -u %s"%user))

def get_nodelist(user):
    return cmd(
        '''squeue -h --state='R' --user=%s -o %%N | ''' % user +
        '''grep -v "CLUSTER" | sort -u | tr '\n' ' ' '''
    ).split(' ')[:-1]

def get_cpus_requested(user):
    return int(cmd(
        '''squeue -h --state='R' --user=%s -o %%C | ''' % user + 
        '''grep -v "CLUSTER" | awk '{ SUM += $1;} END {print SUM }' '''
    ))

def get_mem_requested(user):
    mems = cmd(
        '''sacct -X --state=R --user=%s -n -o"ReqMem,ReqCPUS,ReqNodes"''' % user
    ).split('\n')
    
    mems = [m.strip() for m in mems][:-1]
    total_mem = 0
    # print(mems)
    for x in mems:
        m,c,n = x.split()
        c = int(c)
        n = int(n)
        # mul = 1
        if m[-1] == 'c':
            mul = c
        elif m[-1] == 'n':
            mul = n
        if m[-2] == 'M':
            # print(int(m[:-2])*1000*c)
            total_mem += int(m[:-2])*1000*mul
        elif m[-2] == 'G':
            total_mem += int(m[:-2])*1000000*mul
        elif m[-2] == 'K':
            total_mem += int(m[:-2])*mul
        else:
            print('err')
    return total_mem

def get_cpu_usage(user,nodelist):
    return float(cmd(
        '''clush -w %s -N '''%','.join(nodelist)+
        '''"ps -u %s -o pcpu= " 2>/dev/null | '''%user+
        '''awk 'BEGIN {sum=0} {sum+=$1} END {print sum}' '''
    ))/100

def get_peak_mem(user,nodelist):
    mems = cmd(
        '''clush -w %s -N '''%','.join(nodelist)+
        '''"ps -u %s -o pid= | '''%user+
        '''awk '{ system(\\"grep VmHWM /proc/\\" \$1 \\"/status 2>/dev/null\\") }'" '''
    )
    
    peaks = mems.split('\n')[:-1]
    peaks = [p.split() for p in peaks]
    total_mem = 0
    for _,p,u in peaks:
        if u[0] == 'k':
            total_mem += int(p)
        else:
            print(error)
    return total_mem

def main(user=None):
    if user == None:
        users = get_active_users()
    else:
        users = [user]
    print('user\t\t\tcpu eff\t\tmem eff\t\t alloc cpu\t alloc mem')
    print('-'*85)
    for user in users:
        print('{:10s}'.format(user),end='\t\t')
        try:
          nodelist = get_nodelist(user)
        except:
          print('*** user not found ***')
          continue
        if len(nodelist) == 0:
           print('*** user not running jobs ***')
           continue
        cpus_requested = get_cpus_requested(user)
        cpu_usage = get_cpu_usage(user,nodelist)
        mem_requested = get_mem_requested(user)
        mem_usage = get_peak_mem(user,nodelist)
        cpu_eff = cpu_usage/cpus_requested
        mem_eff = min(0.9999,mem_usage/mem_requested)
        cwarn = ('','')
        mwarn = ('','')
        if cpu_eff < 0.5:
          cwarn = (bcolors.WARNING, bcolors.ENDC)
        if cpu_eff < 0.2:
          cwarn = (bcolors.FAIL, bcolors.ENDC)
        if mem_eff < 0.5:
          mwarn = (bcolors.WARNING, bcolors.ENDC)
        if mem_eff < 0.2:
          mwarn = (bcolors.FAIL, bcolors.ENDC)
        print(cwarn[0]+'%.2f%%'%(cpu_eff*100)+cwarn[1],end='\t\t')
        print(mwarn[0]+'≤ %.0f%%'%(mem_eff*100)+mwarn[1],end='\t\t')
        print('%d\t\t%dG'%(cpus_requested,mem_requested/1e6))

if __name__ == '__main__':
	user = sys.argv[1] if len(sys.argv) > 1 else None
	main(user)
