# filebrowser-downloader
Python script to download data from a file server hosted on filebrowser (https://filebrowser.org/).

AdvanceDownload.py allows partial downloads and partial skipping.
Place the file “set.classB” in the folder where you want the partial download to take place. Then files and folders below that hierarchy are recursively downloaded.
This may be inefficient because it searches through all folders. Therefore, if you place a “set.skip” file, all files and folders below that level will be skipped.
