"""Versioned logical-face metadata and recoverable two-file saves."""
from struct import pack,unpack_from
from binascii import crc32
from .streams import chunks
from .quads import Faces,encode_pairs,decode_pairs


def fingerprint(storage,path):
    size=storage.size(path);crc=0
    if size<0:raise OSError('Cannot read saved file size')
    for part in chunks(storage,path,size,3200):crc=crc32(part,crc)
    return (size,crc)


def read(storage,path,limit):
    size=storage.size(path)
    if size<0 or size>limit:raise ValueError('Invalid editor metadata size')
    data=bytearray()
    for part in chunks(storage,path,size):data.extend(part)
    return data


def encode(signature,pairs,pivot=None):
    from math import isfinite
    present=1 if pivot is not None else 0
    coordinates=tuple(float(value) for value in pivot) if present else (0.0,0.0,0.0)
    if len(coordinates)!=3 or any(not isfinite(value) or abs(value)>1e12 for value in coordinates):
        raise ValueError('Invalid custom pivot')
    data=(pack('<4sIIII',b'S3QE',2,signature[0],signature[1],len(pairs)//2)
          +encode_pairs(pairs)+pack('<B3f',present,*coordinates))
    return data+pack('<I',crc32(data))


def metadata(data,signature):
    from math import isfinite
    if len(data)<24:raise ValueError('Incomplete editor metadata')
    magic,version,size,crc,count=unpack_from('<4sIIII',data)
    if magic!=b'S3QE' or version not in (1,2):raise ValueError('Unsupported editor metadata')
    if (size,crc)!=tuple(signature):raise ValueError('Editor metadata belongs to different geometry')
    expected=24+count*8+(13 if version==2 else 0)
    if len(data)!=expected or unpack_from('<I',data,len(data)-4)[0]!=crc32(data[:-4]):raise ValueError('Corrupt editor metadata')
    pairs=decode_pairs(data[20:20+count*8])
    pivot=None
    if version==2:
        present,x,y,z=unpack_from('<B3f',data,20+count*8)
        if present not in (0,1):raise ValueError('Invalid custom pivot flag')
        if present:
            pivot=(x,y,z)
            if any(not isfinite(value) or abs(value)>1e12 for value in pivot):raise ValueError('Invalid custom pivot')
    return pairs,pivot


def membership(data,signature):
    return metadata(data,signature)[0]


def decode(data,signature,records):
    return Faces(records,membership(data,signature))


def load_steps(storage,path,records,prepared=False,pivot_out=None):
    """Valid empty membership is authoritative; only legacy data is inferred."""
    from .quads import infer_steps,face_steps
    reason='Missing editor metadata'
    if pivot_out is not None:pivot_out[:]=[None]
    if storage.exists(path+'.editor'):
        try:
            pairs,pivot=metadata(read(storage,path+'.editor',64+len(records)//10),fingerprint(storage,path))
            state=yield from face_steps(records,pairs)
            if pivot_out is not None:pivot_out[:]=[pivot]
            return (state if prepared else state.pairs),''
        except (ValueError,OSError) as exc:reason=str(exc)
    pairs=yield from infer_steps(records)
    message=reason+'; inferred '+str(len(pairs)//2)+' quads'
    if prepared:pairs=yield from face_steps(records,pairs)
    return pairs,message


def remove(storage,path):
    if storage.exists(path) and not storage.remove(path):raise OSError('Cannot remove '+path)


def rename(storage,source,destination):
    if not storage.rename(source,destination):raise OSError('Cannot rename '+source)


def matches(storage,path,signature):
    return storage.exists(path) and fingerprint(storage,path)==tuple(signature)


def journal_data(state):
    from json import dumps
    data=dumps(state).encode()
    return pack('<4sI',b'QJ01',crc32(data))+data


def recover(storage,path,rollback=False):
    """Finish an installed pair or roll back both files, retaining evidence on failure."""
    journal=path+'.editor-journal'
    if not storage.exists(journal):return False
    from json import loads
    data=read(storage,journal,8192)
    if len(data)<8 or data[:4]!=b'QJ01' or unpack_from('<I',data,4)[0]!=crc32(data[8:]):raise OSError('Invalid save recovery journal: '+journal)
    try:
        state=loads(bytes(data[8:]))
        if not isinstance(state,dict):raise ValueError()
        items=state['items']
        if not isinstance(items,list) or len(items)!=2:raise ValueError()
        for i,item in enumerate(items):
            if not isinstance(item,dict):raise ValueError()
            expected=path+('.editor' if i else '')
            prefix=path+'.editor-txn-';suffix='.meta' if i else '.sprite3d'
            stage=item['stage']
            if not isinstance(stage,str):raise ValueError()
            number=stage[len(prefix):-len(suffix)]
            if (item['path']!=expected or not stage.startswith(prefix) or not stage.endswith(suffix)
                    or not number or any(c not in '0123456789' for c in number)
                    or item['backup']!=stage+'.bak'):raise ValueError()
            for key in ('old','new'):
                signature=item[key]
                if signature is None and key=='old':continue
                if (not isinstance(signature,list) or len(signature)!=2
                        or any(type(v) is not int or v<0 or v>0xffffffff for v in signature)):raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise OSError('Invalid save recovery entries: '+journal)
    complete=not rollback and all(matches(storage,item['path'],item['new']) for item in items)
    if not complete:
        for item in items:
            target,backup=item['path'],item['backup'];old=item['old']
            if old is None:
                if storage.exists(target):
                    if not matches(storage,target,item['new']):raise OSError('Recovery found an unexpected file: '+target)
                    remove(storage,target)
            elif matches(storage,target,old):pass
            elif matches(storage,backup,old):
                if storage.exists(target):
                    if not matches(storage,target,item['new']):raise OSError('Recovery found an unexpected file: '+target)
                    remove(storage,target)
                rename(storage,backup,target)
            else:raise OSError('Recovery requires original backup: '+backup)
    # The pair is now consistent. Cleanup can be retried without losing originals.
    for item in items:
        remove(storage,item['stage']);remove(storage,item['backup'])
    remove(storage,journal)
    return complete


def save(storage,mesh,path,records,pairs,pivot=None):
    if not path.lower().endswith('.sprite3d'):raise ValueError('Use a .sprite3d filename')
    if storage.is_directory(path) or storage.is_directory(path+'.editor'):raise ValueError('Destination is a directory')
    if not storage.is_directory(path.rsplit('/',1)[0] or '/'):raise ValueError('Destination folder does not exist')
    recover(storage,path)
    index=0
    while True:
        prefix=path+'.editor-txn-'+str(index)
        stages=[prefix+'.sprite3d',prefix+'.meta']
        if not any(storage.exists(p) or storage.exists(p+'.bak') for p in stages):break
        index+=1
    journal=path+'.editor-journal';journal_written=False
    try:
        if not mesh.to_path(stages[0]):raise OSError('Could not write staged geometry')
        size=storage.size(stages[0]);crc=0;offset=0
        if size!=len(records):raise OSError('Incomplete staged geometry')
        for part in chunks(storage,stages[0],size,3200):
            crc=crc32(part,crc)
            for i in range(0,len(part),40):
                if part[i:i+39]!=records[offset+i:offset+i+39]:raise OSError('Staged geometry differs from document')
            offset+=len(part)
        signature=(size,crc)
        # Exact serialized geometry equality permits validating membership once
        # against the source, without allocating a duplicate native mesh.
        Faces(records,pairs)
        data=encode(signature,pairs,pivot)
        if not storage.write(stages[1],data,'wb'):raise OSError('Could not write staged editor metadata')
        if read(storage,stages[1],len(data))!=data:raise OSError('Incomplete staged editor metadata')
        signatures=(signature,(len(data),crc32(data)))
        items=[]
        for index,(target,stage) in enumerate(zip((path,path+'.editor'),stages)):
            items.append({'path':target,'stage':stage,'backup':stage+'.bak','old':fingerprint(storage,target) if storage.exists(target) else None,'new':signatures[index]})
        data=journal_data({'items':items})
        if not storage.write(journal,data,'wb'):raise OSError('Could not write save recovery journal')
        if read(storage,journal,len(data))!=data:raise OSError('Incomplete save recovery journal')
        journal_written=True
        for item in items:
            if item['old'] is not None:rename(storage,item['path'],item['backup'])
        for item in items:rename(storage,item['stage'],item['path'])
        if not all(matches(storage,item['path'],item['new']) for item in items):raise OSError('Saved pair verification failed')
    except Exception as exc:
        if journal_written:
            try:recover(storage,path,True)
            except Exception as recovery:raise OSError(str(exc)+'; recovery pending: '+str(recovery))
        else:
            # No destination has been touched before the journal is verified.
            for stage in stages:remove(storage,stage)
            remove(storage,journal)
        raise
    try:
        # Installation was just verified; recovery rechecks hashes only after a restart.
        for item in items:
            remove(storage,item['stage']);remove(storage,item['backup'])
        remove(storage,journal)
    except (OSError,ValueError,MemoryError):return 'Saved; backup cleanup will retry on open'
    return ''
