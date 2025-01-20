#!/usr/bin/python3
# GeckoBuild - GeckoNerd, 2025
from subprocess import PIPE
import click
import logging
import pathlib
import sys
import asyncio
import os
import inspect
import json
import traceback

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

_tasks = []
filecache = {}

class KBuildTask:
    def __init__(self, fn, deps):
        global _tasks

        self.fn = fn
        self.deps = deps

        self.finished = False
        self.finished_because_nothing_changed = False
        self.run_anyway = False
        _tasks.append(self)
    
    async def run(self):
        self.finished = False
        self.finished_because_nothing_changed = False

        # this is used to find task name in call stack
        _idenme_kbuildtask_name_ = self.fn.__name__

        dep_unchanged = []
        for dep in self.deps:
            if isinstance(dep, KBuildTask):
                pass
            elif isinstance(dep, str):
                if run_anyway:
                    continue
                if not os.path.exists(dep):
                    raise Exception(f"File '{dep}' does not exist.")
                # calculate cache of file and compare to cache
                dep_unchanged.append(dep in filecache and filecache[dep] == os.stat(dep).st_mtime)                    
            else:
                raise TypeError(f"Invalid dependency type: {type(dep)}")
        if len(dep_unchanged) > 0:
            if (all(dep_unchanged) and not self.run_anyway) and not run_anyway:
                log(f"Skipped task '{self.fn.__name__}' because files weren't changed since last build.")
                self.finished = True
                self.finished_because_nothing_changed = True
                return
            
        for dep in self.deps:
            if isinstance(dep, KBuildTask):
                # if task ran before setting anyway flag
                if dep.anyway and dep.finished_because_nothing_changed:
                    await dep.run()
        while any((not dep.finished for dep in self.deps if isinstance(dep, KBuildTask))):
            await asyncio.sleep(0.01)
        try:
            await self.fn()
        except Exception as e:
            e._kbuild_exception_source = self
            raise e
        
        # write files to cache
        for dep in self.deps:
            if isinstance(dep, str):
                filecache[dep] = os.stat(dep).st_mtime
        self.finished = True
    
    async def anyway(self):
        self.run_anyway = True
        return self

def task(*deps):
    def inner(fn):
        assert asyncio.iscoroutinefunction(fn), "Tasks should be marked as 'async'"
        return KBuildTask(fn, deps)
    return inner

run_anyway = False
@click.command()
@click.option("-B", "--build-anyway", is_flag=True, help="Runs provided tasks independantly of file checks.")
def build(build_anyway):
    global run_anyway
    run_anyway = build_anyway
    async def _run():
        global filecache

        pathlib.Path("./_build/cache/").mkdir(parents=True, exist_ok=True)
        if not os.path.exists("./_build/cache/geckobuild.filecache.json"):
            with open("./_build/cache/geckobuild.filecache.json", "w") as f:
                f.write("{}")
        else:
            filecache = json.loads(open("./_build/cache/geckobuild.filecache.json", "r").read())
        try:
            await asyncio.gather(*[task.run() for task in _tasks])
        except Exception as e:
            logging.error(e)
            if hasattr(e, "_kbuild_exception_source"):
                logging.error(f"Build failed on task '{e._kbuild_exception_source.fn.__name__}', exit code 1")
            else:
                traceback.print_exception(e)
                logging.exception(e)
                logging.error(f"Could not determine failed task, exit code 1")
            sys.exit(1)

        # only if no errors occurred
        with open("./_build/cache/geckobuild.filecache.json", "w") as f:
            f.write(json.dumps(filecache))
    asyncio.run(_run())

async def run(*command, raise_nonzero=True):
    taskname = [f.frame.f_locals['_idenme_kbuildtask_name_'] for f in inspect.stack() if f.function == "run" and "_idenme_kbuildtask_name_" in f.frame.f_locals][0]
    command = [str(c) for c in command]
    log(taskname + ": " + ' '.join(command))
    async def runreader(pipe):
        while True:
            line = await pipe.readline()
            if len(line) == 0:
                break
            if not line.endswith(b'\n'):
                line += b'\n'
            print(f"{taskname}: {line.decode()}", end='')
    p = await asyncio.create_subprocess_exec(*command, stdout=PIPE, stderr=PIPE)
    asyncio.ensure_future(runreader(p.stdout))
    asyncio.ensure_future(runreader(p.stderr))
    await p.wait()
    if raise_nonzero and p.returncode != 0:
        raise Exception(f"Command '{' '.join(command)}' exited with code {p.returncode}")
    return p.returncode

sleep = asyncio.sleep
log = logging.info
__all__ = ['task', 'build', 'sleep', 'log', 'run']
