import os
import re
import subprocess
from cudatext import *

LOG = False
MY_DECOR_COLOR = 0xFF
DIFF_TAG = app_proc(PROC_GET_UNIQUE_TAG, '')

class GitManager:
    def __init__(self):
        self.git = 'git'
        self.prefix = ''
        self.filename = ''
        self.last_error = ''

    def run_git(self, args, silence_errors=False):
        try:
            self.last_error = ''
            cmd = [self.git] + args
            cwd = self.getcwd()
            my_env = os.environ.copy()
            # removing GIT environment vars if any, they are interfering with our git calls
            my_env = { k:v for k,v in my_env.items() if not k.upper().startswith('GIT_') }
            if os.name=='nt':
                # make sure console does not come up
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                p = subprocess.Popen(cmd,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     cwd=cwd,
                                     startupinfo=startupinfo,
                                     env=my_env)
            else:
                my_env["PATH"] = "/usr/local/bin:/usr/bin:" + my_env["PATH"]
                my_env["LANG"] = "en_US"
                p = subprocess.Popen(cmd,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     cwd=cwd,
                                     env=my_env)
    
            #p.wait() # makes deadlock if process gives lot of data
            stdoutdata, stderrdata = p.communicate()
            out_text = stdoutdata.decode('utf-8', errors='replace')
            error_text = stderrdata.decode('utf-8', errors='replace') if not silence_errors else ''
    
            # don't always show error_text, it may be normal message for 'push' action
            if (
                'fatal: ' in error_text or
                'error: ' in error_text
            ):
                print("NOTE: Git Status: ", error_text)
                self.last_error = error_text
    
            ''' #debug
            if stdoutdata:
                print('Git for:', repr(args), ', gets:', stdoutdata)
            else:
                print('Git fails:', repr(args))
            '''
        except Exception as e:
            raise Exception('{}, command: {}'.format(e, ' '.join(cmd)))

        return (p.returncode, out_text)

    def getcwd(self):
        f = self.filename
        cwd = None
        if f:
            cwd = os.path.dirname(f)
        return cwd

    def branch(self):
        (exit_code, output) = self.run_git(["status", "-u", "no"], silence_errors=True)
        if exit_code != 0:
            return ''
        m = re.search(r"(?:at|branch)\s(.*?)\n",output)
        if m:
            return m.group(1)
        else:
            return ''

    def is_dirty(self):
        (exit_code, output) = self.run_git(["diff-index", "--quiet", "HEAD"], silence_errors=True)
        return exit_code == 1

    def commit_count(self):
        (exit_code, output) = self.run_git(["rev-list", "--count", "HEAD"], silence_errors=True)
        if exit_code != 0:
            return 0
        return int(output)

    ### This code shows dirty state when we have untacked files, bad.
    #def is_dirty(self):
    #    (exit_code, output) = self.run_git(["status", "-s"])
    #    return bool(output)

    def unpushed_info__old(self, branch):
        a, b = 0, 0
        if branch:
            exit_code, output = self.run_git(["branch", "-v"])
            if output:
                m = re.search(r"\* .*?\[behind ([0-9])+\]", output, flags=re.MULTILINE)
                if m:
                    a = int(m.group(1))
                m = re.search(r"\* .*?\[ahead ([0-9])+\]", output, flags=re.MULTILINE)
                if m:
                    b = int(m.group(1))
        return (a, b)

    def unpushed_info(self, branch):
        if branch:
            (exit_code, output) = self.run_git(
                ['rev-list', '--left-right', '--count', 'origin/'+branch+'...'+branch],
                silence_errors=True
            )
            m = re.search(r"(\d+)\s+(\d+)", output)
            if m:
                return (int(m.group(1)), int(m.group(2)))
            else:
                return (0,0)
        return (0,0)

    def diff(self, filename_):
        if filename_ != ed.get_filename():
            return
        exit_code, output = self.run_git(["diff", "-U0", filename_])
        if exit_code != 0:
            return ''
        ed.decor(DECOR_DELETE_BY_TAG, tag=DIFF_TAG)
        parts = re.findall(r"@@ \-(.*) @@", output)
        lines_ = []
        for part in parts:
            lines = part.split(' +', maxsplit=1)
            line = lines[1]
            parts_ = line.split(',', maxsplit=1)
            if len(parts_) == 2 and isinstance(parts_, list):
                lines_.append(parts_)
            else:
                lines_.append(line)
        if lines_:
            for line_ in lines_:
                if len(line_) == 2 and isinstance(line_, list):
                    begin_ = int(line_[0]) - 1
                    end_ = int(line_[0]) + int(line_[1]) - 1
                    if begin_ == end_:
                        ed.decor(DECOR_SET, line=begin_, tag=DIFF_TAG, text='', color=MY_DECOR_COLOR)
                    else:
                        for l in range(begin_, end_):
                            ed.decor(DECOR_SET, line=l, tag=DIFF_TAG, text='', color=MY_DECOR_COLOR)
                else:
                    line__ = int(line_) - 1
                    ed.decor(DECOR_SET, line=line__, tag=DIFF_TAG, text='', color=MY_DECOR_COLOR)

        return lines_

    def badge(self, filename):
        if not filename:
            return ""
        if not os.path.isfile(filename):
            return ""
        if filename != ed.get_filename():
            return
            
        pass;       LOG and print("getting badge:", filename)

        self.filename = filename
        self.diff(filename)

        branch = self.branch()
        if not branch:
            return ""
        ret = branch
        if self.is_dirty():
            ret = ret + "*"
        a, b = self.unpushed_info(branch)
        if a:
            ret = ret + "-%d" % a
        if b:
            ret = ret + "+%d" % b
        return self.prefix + ret
