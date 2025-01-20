# geckobuild
GeckoBuild - simple async build system in Python. It includes a way to build multiple tasks asynchronously, while still keeping ability for tasks to depend on each other and on files.

# Usage
Here's an example build script that uses GeckoBuild:
```py
#!/usr/bin/python3
from geckobuild import *

@task()
async def wait_and_say_hello():
    print("Waiting...")
    await sleep(1)
    print("Hello!")

# @task arguments are dependencies - strings are files, objects are tasks
@task("tasks.txt", wait_and_say_hello)
async def hello():
    print("Hello, world!")
    with open("tasks.txt", "r") as r:
      print(r.read())

# read command line arguments and execute tasks
build()
```

# Licensing
BSD 3-clause. Read LICENSE for more.
