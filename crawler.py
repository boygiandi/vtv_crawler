import requests, re, os, subprocess, time, sys

def current_dir():
	return os.path.dirname(os.path.realpath(__file__))

def exec_shell(cmd, _return=True, _debug=True):
	if _debug:
		print cmd
	if _return:
		p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
		response = p.stdout.read().strip()
		p.stdout.close()
		p.stdin.close()
		return response
	else:
		subprocess.call(cmd, shell=True)

if len(sys.argv)<2:
	print "not enough parameters"
	sys.exit()

root_dir = "%s/%s"%(current_dir(), sys.argv[1])
exec_shell("mkdir -p %s && rm -f %s/*.ts"%(root_dir, root_dir))

s = requests.Session()
watch_url = "http://vtv.vn/truyen-hinh-truc-tuyen/%s.htm"%sys.argv[1]
get_quality = "desktop"
s.headers.update({'Referer': watch_url})

def generate_m3u8(list_video):
	template = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:%s
"""%list_video[0].split("-")[-1].split(".")[0]
	for item in list_video:
		template += """#EXTINF:2.000000,
%s
"""%item.split("/")[-1]

	return template

while True:
	exec_shell('find %s/ -maxdepth 1 -mmin +30 -type f -name "*.ts" -exec rm -f {} \;'%root_dir)
	valid = True
	r = s.get(watch_url, timeout=5)
	m3u8_master = r.content.split("<iframe")[1][0:200].split('src="')[1].split('"')[0]
	try:
		r = s.get(m3u8_master, timeout=15)
	except Exception,e:
		time.sleep(1)
		continue

	video_links = {}
	regex = r"(.*\.m3u8)"
	matches = re.finditer(regex, r.content)
	video_root = "/".join(r.url.split("/")[:-1])
	for matchNum, match in enumerate(matches):
		quality = "mobile" if "_m.m3u8" in match.group(1) else "desktop"
		video_links[quality] = "%s/%s"%(video_root, match.group(1))

	if len(video_links.keys())==0:
		print r.content
		break

	all_m3u8 = []
	url = video_links[get_quality] if get_quality in video_links else video_links[video_links.keys()[0]]
	while True:
		try:
			m3u8_content = s.get(url, timeout=5).content
		except Exception,e:
			continue
		regex = r"(.*\.ts)"
		matches = re.finditer(regex, m3u8_content)
		for matchNum, match in enumerate(matches):
			video_file = match.group(1)
			if not video_file in all_m3u8:
				video_url = "%s/%s"%(video_root, video_file)
				video_path = "%s/%s"%(root_dir, video_file)
				cmd = "wget -qO- '%s' | zcat > '%s' &"%(video_url, video_path)
				exec_shell(cmd)
				if len(all_m3u8)>20:
					exec_shell("rm -f %s/%s"%(root_dir, all_m3u8[0]))
					all_m3u8 = all_m3u8[1:]
				if not os.path.isfile(video_path) or os.path.getsize(video_path)==0:
					print "download failed %s"%video_path
					valid = False
				else:
					all_m3u8.append(video_file)

		if len(all_m3u8):
			with open("%s/index.m3u8"%root_dir, "w+") as f:
				f.write(generate_m3u8(all_m3u8))
		if not valid:
			break
		time.sleep(1)

