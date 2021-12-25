from rich import print

from cookiebakery import Workflow

w = Workflow.from_file("tests/napari-plugin2.yaml")
out = w.execute()

print(out)
