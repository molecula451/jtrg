#!/usr/bin/env python3
import asyncio
import pathlib
import sys

import yapapi
from yapapi.log import enable_default_logger, log_summary, log_event_repr  # noqa
from yapapi.runner import Engine, Task, vm
from yapapi.runner.ctx import WorkContext
from datetime import timedelta

# For importing `utils.py`:
script_dir = pathlib.Path(__file__).resolve().parent
parent_directory = script_dir.parent
sys.stderr.write(f"Adding {parent_directory} to sys.path.\n")
sys.path.append(str(parent_directory))
import utils  # imported locally

async def main(subnet_tag: str, node_count: int, timeout_seconds: int, password: str):
    print(f"Stats: Nodes = {node_count}, Timeout = {timeout_seconds}s, Password = {password}")

    if node_count < 2:
        raise Exception("Invalid node_count. There must be 2 or more nodes.")
    else:
        print("Running more than 2 nodes")

    package = await vm.repo(
        image_hash="a6722779ca397520db82f354684a46a13c473aca04e38b91ec32755e",
        min_mem_gib=4,
        min_storage_gib=3.0,
    )

    async def ripper(ctx: WorkContext, tasks):
        async for task in tasks:
            output_file = f"out_{str(task.data['node'])}.txt"
            #ctx.send_file('ripper.sh', '/golem/entrypoints/ripper.sh') #in case you want to send your modify it bash uncomment
            ctx.run('bin/sh', '/golem/entrypoints/ripper.sh', str(task.data['node']), str(task.data['nodes']), str(timeout_seconds), password)
            ctx.log("task data is:")
            ctx.log(task.data)
            ctx.download_file("/golem/output/result.txt", output_file)
            yield ctx.commit()
            task.accept_task(result=output_file)

        ctx.log("hmm.. it looks like we got some passwords")

    # iterator over the frame indices that we want to render
    nodes = [Task(data={'node': i+1, 'nodes': node_count}) for i in range(node_count)]

    init_overhead: timedelta = timedelta(minutes=10)

    # By passing `event_emitter=log_summary()` we enable summary logging.
    # See the documentation of the `yapapi.log` module on how to set
    # the level of detail and format of the logged information.
    async with Engine(
        package=package,
        max_workers=node_count,
        budget=30.0,
        timeout=init_overhead + timedelta(minutes=node_count * 2),
        subnet_tag=subnet_tag,
        event_emitter=log_summary(log_event_repr),
    ) as engine:

        async for task in engine.map(ripper, nodes):
            print(
                f"{utils.TEXT_COLOR_CYAN}"
                f"Task computed: {task}, result: {task.output}"
                f"{utils.TEXT_COLOR_DEFAULT}"
            )
        
    # Process done, so remind the user of the parameters and show the results
    print(f"Parameters: Nodes = {node_count}, Timeout = {timeout_seconds}s, Password = {password}")
    for i in range(node_count):
            output_file = f"out_{str(i+1)}.txt"
            with open(output_file) as f:
                lines = f.readlines()

            echoer_message = f"Ripper {i+1} did not find the password"
            for line in lines:
                if "?" in line:
                    echoer_message = f"{utils.TEXT_COLOR_GREEN}Worker {i+1} found the password: {line[2:].strip()}{utils.TEXT_COLOR_DEFAULT}"
                    break

            print(echoer_message)


if __name__ == "__main__":
    parser = utils.build_parser("John the Ripper")
    parser.add_argument("node_count")
    parser.add_argument("timeout_seconds")
    parser.add_argument("password")
    parser.set_defaults(log_file="john.log", node_count="4", timeout_seconds="5", password="golem")
    args = parser.parse_args()

    enable_default_logger(log_file=args.log_file)
    loop = asyncio.get_event_loop()
    subnet = args.subnet_tag
    sys.stderr.write(
        f"yapapi version: {utils.TEXT_COLOR_YELLOW}{yapapi.__version__}{utils.TEXT_COLOR_DEFAULT}\n"
    )
    sys.stderr.write(f"Using subnet: {utils.TEXT_COLOR_YELLOW}{subnet}{utils.TEXT_COLOR_DEFAULT}\n")
    task = loop.create_task(main(subnet_tag=args.subnet_tag, node_count=int(args.node_count), timeout_seconds=int(args.timeout_seconds), password=args.password))
    try:
        asyncio.get_event_loop().run_until_complete(task)

    except (Exception, KeyboardInterrupt) as e:
        print(e)
        task.cancel()
        asyncio.get_event_loop().run_until_complete(task)
