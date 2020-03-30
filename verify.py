import json
import os
from PIL import Image

_path = os.path.join(os.getcwd(), "Issues")
_links_path = os.path.join(os.getcwd(), "link_list.txt")

links = []
with open(_links_path, 'r') as f:
    for line in f:
        links.append(line)


directories = [x[0] for x in os.walk(_path)]

print(f"Num Dirs: {len(directories)}\nNum Links: {len(links)}")

meta_links = []
runningTotal = 0

for directory in directories:
    # open metadata and check dir length
    if directory.split('/')[-1:][0] == "Issues":
        continue

    meta = {}
    with open(os.path.join(directory, "metadata.json")) as p:
        meta = json.load(p)

    meta_links.append(meta['starting_url'])

    files = [f.strip() for f in os.listdir(os.path.join(_path, directory))]

    if len(files) -1 != int(meta['num_pages']):
        print(f"Folder: {directory}, NumFiles vs Expected: {len(files)-1}, {meta['num_pages']}")

    
    corrupt = []

    for image_path in files:
        if image_path[-3:] == 'jpg':
            runningTotal += 1
            try:
                #img = Image.open(os.path.join(directory, image_path)) # open the image file
                #img.verify() # verify that it is, in fact an image
                pass
            except (IOError, SyntaxError) as e:
                print(f"File: {directory}/{image_path} is corrupt")
                corrupt.append(directory + "/" +image_path)

    with open("corrupt.txt", '+w') as w:
        [w.write(line + '\n') for line in corrupt]
    
with open("actual_links.txt", '+w') as g:
    [g.write(line + '\n') for line in meta_links]

print(runningTotal)