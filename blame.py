#!/usr/bin/env python3

# usage:
# ./blame.py
# prove that nothing is ever your fault

class bcolors:
		HEADER = '\033[95m'
		OKBLUE = '\033[94m'
		OKGREEN = '\033[92m'
		WARNING = '\033[93m'
		FAIL = '\033[91m'
		ENDC = '\033[0m'
		BOLD = '\033[1m'
		UNDERLINE = '\033[4m'

def blame(user=None):
		if user == None:
				users = get_active_users()
		else:
				users = [user]
		user_data = []
		total_cpu = 0
		total_mem = 0
		for user in users:
				nodelist = get_nodelist(user)
				cpus_requested = get_cpus_requested(user)
				cpu_usage = get_cpu_usage(user,nodelist)
				mem_requested = get_mem_requested(user)
				mem_usage = get_peak_mem(user,nodelist)
				
				num_nodes = len(nodelist)
				cpus_per_node = cpus_requested/len(nodelist)
				mem_per_node = mem_requested/len(nodelist)
				
				total_cpu += cpus_requested
				total_mem += mem_requested
				
				prop_cpu = cpus_requested/(50*56)
				prop_mem = mem_requested/(50*126*1e6)
				
				wasted_cpu = (cpus_requested - cpu_usage)/(50*56)
				wasted_mem = (mem_requested - mem_usage)/(50*126*1e6)
				
				user_data.append((
						wasted_cpu,
						user,
						'%.1f%%'%(prop_cpu*100),
						'%.1f%%'%(prop_mem*100),
						(red('%.1f%%') if wasted_cpu > 0.1 else 
							yellow('%.1f%%') if wasted_cpu > 0.02 else '%.1f%%')%(wasted_cpu*100),
						(red('%.1f%%') if wasted_mem > 0.1 else 
							yellow('%.1f%%') if wasted_mem > 0.02 else '%.1f%%')%(wasted_mem*100),
						str(num_nodes),
						'%.1f'%cpus_per_node,
						'%.1fG'%(mem_per_node/1e6)
				))
				
		user_data = sorted(user_data,reverse=True)
		
		print('Percent of resources allocated per user')
		print('\t           alloc            wasted					 ')
		print('user\t        cpu\t mem\t cpu\t mem\t num_nodes\t'+
					'cpus_per_node\t mem_per_node')
		for r in user_data:
				print('{:10s}'.format(r[1]),end='\t')
				print('\t'.join(r[2:6]),end='\t\t')
				print('\t\t'.join(r[6:]))
		print()
		print('Total swarm allocation')
		print()
		print('cpu\t mem')
		total_cpu_prop = total_cpu / (50*56)
		total_mem_prop = total_mem / (50*126*1e6)
		print(
			(red('%.2f') if total_cpu_prop > 0.9 else
			 yellow('%.2f') if total_cpu_prop > 0.75 else
			 green('%.2f')) % total_cpu_prop, end='\t')
		print(
			(red('%.2f') if total_mem_prop > 0.9 else
			 yellow('%.2f') if total_mem_prop > 0.75 else
			 green('%.2f')) % total_mem_prop)
		print()
		print()
		print('Resources available')
		print()
		print('cpu\t mem')
		print('%d\t %.1fG'%((50*56)-total_cpu, (50*126*1e6 - total_mem)/1e6))
# print('%.2f\t %.2f'%(total_cpu/(50*56),total_mem/(50*126*1e6)))

def red(s):
	return bcolors.FAIL + s + bcolors.ENDC

def green(s):
	return bcolors.OKGREEN + s + bcolors.ENDC

def yellow(s):
	return bcolors.WARNING + s + bcolors.ENDC
	 
def get_conflicts():
		from pprint import pprint
		from collections import OrderedDict
		# res = cmd('squeue -o %r,%Q,%C,%D,%m,%u,%j').split('\n')[:-1]
		res = cmd('squeue -o %r,%Q,%C,%D,%m,%u').split('\n')[:-1]
		headers = res[0]
		res = [r.split(',') for r in res][1:]
		print('Conflicts:')
		print('\t'.join(headers.split(',')))
		conflicts = [r for r in res if r[0] == 'Resources']
		conflict_strs = ['\t'.join(r) for r in conflicts]
		conflict_cts = OrderedDict()
		for c in conflict_strs:
			if c not in conflict_cts:
				conflict_cts[c] = 0
			conflict_cts[c] += 1
		if len(conflicts) == 0:
				print(' ** no jobs awaiting resources ** ')
		else:
			for c in conflict_cts:
				print(c+'\t x'+str(conflict_cts[c]))
				# pprint(conflicts)
		print()
		waiting = [r for r in res if r[0] != 'None' and r[0] != 'Resources']
		waiting_strs = ['\t'.join(r) for r in waiting]
		waiting_cts = OrderedDict()
		for c in waiting_strs:
			if c not in waiting_cts:
				waiting_cts[c] = 0
			waiting_cts[c] += 1
		print('Waiting:')
		print('\t'.join(headers.split(',')))
		if len(waiting) == 0:
				print(' ** no jobs pending ** ')
		else:
			for c in waiting_cts:
				print(c+'\t x'+str(waiting_cts[c]))

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

import subprocess
import sys

if __name__ == '__main__':

	print()
	blame() 
	print()
	if len(sys.argv) > 1:
		get_conflicts()
		print()
