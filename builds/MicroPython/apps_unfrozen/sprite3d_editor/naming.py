"""Name-only document prompts and validated destinations."""


def filename(text):
    if any(ord(c)<32 or ord(c)==127 for c in text):
        raise ValueError("Name cannot contain control characters")
    name = text.strip()
    while name.lower().endswith('.sprite3d'):
        name = name[:-9]
    if not name or name in ('.','..'):
        raise ValueError('Enter a file name')
    if name.endswith('.') or name.endswith(' '):
        raise ValueError('Name cannot end with a dot or space')
    if any(ord(c)<32 or ord(c)==127 or c in '/\\:*?"<>|' for c in name):
        raise ValueError('Use a name without path or reserved characters')
    result = name+'.sprite3d'
    if len(result.encode())>255:
        raise ValueError('File name is too long')
    return result


class NamingTools:
    def begin_name(self, purpose, text=None, error=None):
        if text is None:
            base = self.path.rsplit('/',1)[-1]
            if base.lower().endswith('.sprite3d'):
                base = base[:-9]
            text = '' if purpose=='New' else base+'-copy' if base else 'untitled'
        keyboard = self.vm.keyboard
        keyboard.reset()
        self.name_purpose = purpose
        self.name_directory = self.directory
        keyboard.title = (error or purpose+' name')+' | '+self.name_directory
        keyboard.response = text
        self.save_as = True
        keyboard.run(force=True)
        keyboard.run(force=True)

    def run_name(self, inputs):
        from picoware.system.buttons import BUTTON_BACK,BUTTON_ESCAPE
        self._scene_keys.clear()
        keyboard = self.vm.keyboard
        if inputs.button in (BUTTON_BACK,BUTTON_ESCAPE):
            inputs.reset()
            keyboard.reset()
            self.save_as = False
            self.save_action = None
        elif keyboard.is_finished:
            text = keyboard.response
            purpose = self.name_purpose
            keyboard.reset()
            self.save_as = False
            try:
                path = self.name_directory.rstrip('/')+'/'+filename(text)
                exists = self.vm.storage.exists(path)
                if purpose=='New':
                    if exists:
                        raise ValueError('Name already exists; choose another')
                    self.new_document(path)
                elif exists:
                    self.pending_save = path
                    self.dialog = ('Replace existing file?',path)
                else:
                    self.save_and_continue(path)
            except ValueError as exc:
                self.begin_name(purpose,text,str(exc))
                return
            except (OSError,MemoryError) as exc:
                self.save_action = None
                self.begin_name(purpose,text,str(exc) or 'Not enough memory')
                return
        elif not keyboard.run():
            keyboard.reset()
            self.save_as = False
            self.save_action = None
        if not self.save_as:
            self.draw_frame()
