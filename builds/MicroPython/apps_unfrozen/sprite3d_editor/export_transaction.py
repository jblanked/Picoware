"""Recoverable single-asset replacement, with staging ownership recorded first."""
from binascii import crc32
from struct import pack,unpack
from .quadfile import fingerprint,matches,read,remove,rename


def paths(path,kind):
    base=path+'.'+kind
    return base+'-stage'+('.bin' if kind=='mesh-export' else ''),base+'-backup',base+'-journal',base+'-ready'


def quarantine(storage,path):
    index=0
    while storage.exists(path+'.preserved-'+str(index)):index+=1
    rename(storage,path,path+'.preserved-'+str(index))


def read_state(storage,path):
    from json import loads
    raw=read(storage,path,2048)
    if raw[:4]==b'EX01':
        if len(raw)<8 or unpack('<I',raw[4:8])[0]!=crc32(raw[8:]):raise OSError('Corrupt export journal: '+path)
        raw=raw[8:]
    state=loads(raw)
    if not isinstance(state,dict) or set(state)!=set(('old','new')):raise OSError('Invalid export journal: '+path)
    for sig in state.values():
        if sig is not None and (not isinstance(sig,list) or len(sig)!=2 or any(type(v)!=int or not 0<=v<=0xffffffff for v in sig)):
            raise OSError('Invalid export signature: '+path)
    return state


def write_state(storage,path,state):
    from json import dumps
    payload=dumps(state).encode();raw=b'EX01'+pack('<I',crc32(payload))+payload
    if not storage.write(path,raw,'wb') or read(storage,path,len(raw))!=raw:raise OSError('Cannot verify export journal: '+path)


def recover(storage,path,kind):
    stage,backup,journal,ready=paths(path,kind)
    state=None
    if storage.exists(journal):
        try:state=read_state(storage,journal)
        except (OSError,ValueError,TypeError):
            if not storage.exists(ready):
                if storage.exists(backup):raise
                # Interrupted initial journal write cannot have moved the destination.
                quarantine(storage,journal)
                if storage.exists(stage):quarantine(storage,stage)
                return
            # A verified ready record can recover even if the staging record is damaged.
            state=read_state(storage,ready)
            if state['new'] is None:raise OSError('Invalid ready export journal')
    if storage.exists(ready):
        try:
            committed=read_state(storage,ready)
            if committed['new'] is None or (state is not None and committed['old']!=state['old']):raise ValueError('Mismatched export journal')
        except (OSError,ValueError,TypeError):
            # A partial ready record precedes any destination rename.
            if state is None or state['new'] is not None or storage.exists(backup):raise
            if state['old'] is None:
                if storage.exists(path):raise OSError('Unexpected export destination')
            elif not matches(storage,path,state['old']):raise OSError('Original export changed')
        else:state=committed
    if state is None:
        if storage.exists(backup):raise OSError('Export backup needs recovery: '+backup)
        if storage.exists(stage):quarantine(storage,stage)
        return
    old,new=state['old'],state['new']
    if new is not None and matches(storage,path,new):pass
    elif old is not None and matches(storage,path,old):pass
    elif old is not None and matches(storage,backup,old):
        if storage.exists(path):quarantine(storage,path)
        rename(storage,backup,path)
    elif old is None:
        if storage.exists(path):
            if new is None:raise OSError('Unexpected export destination')
            quarantine(storage,path)
    else:raise OSError('Export backup needs recovery: '+backup)
    remove(storage,stage);remove(storage,backup)
    # Keep the ready signature until last so cleanup itself is recoverable.
    remove(storage,journal);remove(storage,ready)


def begin(storage,path,kind):
    recover(storage,path,kind)
    stage,backup,journal,ready=paths(path,kind)
    state={'old':fingerprint(storage,path) if storage.exists(path) else None,'new':None}
    try:write_state(storage,journal,state)
    except Exception:
        remove(storage,journal)
        raise
    return stage,state


def commit(storage,path,kind,state,signature):
    stage,backup,journal,ready=paths(path,kind)
    if not matches(storage,stage,signature):raise OSError('Staged export differs from generated data')
    state={'old':state['old'],'new':signature}
    write_state(storage,ready,state)
    if state['old'] is not None:rename(storage,path,backup)
    rename(storage,stage,path)
    if not matches(storage,path,signature):raise OSError('Export verification failed')
