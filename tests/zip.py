from picoware.system.view_manager import ViewManager
from picoware.system.app_loader import AppLoader
from picoware.system.drivers.zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
from gc import collect

collect()

vm = ViewManager()
path = "/sd/test.zip"

if vm.storage.mount_vfs():
    # List the information from a .zip archive
    print('\nListing information')
    with ZipFile(path, 'r') as archive: 
        for info in archive.infolist(): 
            print(info.filename)
            print('\tSystem:\t\t' + str(info.create_system) + '(0 = Windows, 3 = Unix)') 
            print('\tZIP version:\t' + str(info.create_version)) 
            print('\tCompressed:\t' + str(info.compress_size) + ' bytes') 
            print('\tUncompressed:\t' + str(info.file_size) + ' bytes') 
    
    # Read a file from inside .zip archive
    # print('\nReading file')
    # with ZipFile(path) as myzip:
    #     with myzip.open('test.txt') as myfile:
    #         print(myfile.read())
