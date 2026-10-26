"""Small native UI theme; no web runtime or background worker."""
import json
import os
import tkinter as tk
from pathlib import Path

PALETTES = {
    'dark': dict(bg='#10151c', panel='#19212c', text='#eef3fa', muted='#a7b4c7',
                 accent='#329df4', selected='#213e59', border='#2b3747', preview='#090d12'),
    'light': dict(bg='#f4f7fb', panel='#ffffff', text='#14202c', muted='#536477',
                  accent='#096fc2', selected='#e0efff', border='#d6e0ec', preview='#e8eef6'),
}

def load_theme(storage):
    try:
        name = json.loads((Path(storage)/'interface.json').read_text())['theme']
        return name if name in PALETTES else 'dark'
    except (OSError, ValueError, KeyError, TypeError):
        return 'dark'

def save_theme(storage, name):
    if name not in PALETTES:
        raise ValueError('Unknown theme')
    folder = Path(storage)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder/'interface.json.tmp'
    temporary.write_text(json.dumps({'theme': name}), encoding='utf-8')
    os.replace(temporary, folder/'interface.json')

def apply_theme(style, window, name):
    p = PALETTES[name]
    window.configure(background=p['bg'])
    style.configure('.', font=('Segoe UI', 11, 'bold'), background=p['panel'], foreground=p['text'])
    style.configure('TFrame', background=p['bg'])
    style.configure('Panel.TFrame', background=p['panel'])
    style.configure('TLabel', background=p['bg'], foreground=p['text'])
    style.configure('Muted.TLabel', foreground=p['muted'])
    style.configure('Help.TLabel', font=('Segoe UI', 10), foreground=p['muted'])
    style.configure('Status.TLabel', font=('Segoe UI', 10, 'bold'), background=p['panel'])
    style.configure('Footer.TFrame', background=p['panel'])
    style.configure('Footer.TLabel', font=('Segoe UI', 10, 'bold'), background=p['panel'], foreground=p['muted'])
    style.configure('Panel.TLabel', background=p['panel'], foreground=p['text'])
    style.configure('TButton', padding=(12, 9), borderwidth=0, relief='flat', background=p['panel'], foreground=p['text'])
    style.map('TButton', background=[('active', p['selected']), ('pressed', p['selected'])], foreground=[('disabled',p['muted'])])
    style.configure('Primary.TButton', background=p['accent'], foreground='#ffffff', font=('Segoe UI',11,'bold'))
    style.map('Primary.TButton', background=[('active', '#1689df'),('disabled',p['border'])])
    style.configure('Nav.TButton', anchor='w', padding=(18,16), background=p['bg'])
    style.configure('Selected.Nav.TButton', background=p['selected'], foreground=p['accent'])
    style.configure('TCheckbutton', background=p['bg'], foreground=p['text'], padding=6)
    style.map('TCheckbutton', background=[('active',p['selected'])])
    style.configure('TRadiobutton', background=p['bg'], foreground=p['text'], padding=6)
    style.layout('TRadiobutton', [('Radiobutton.padding', {'children':[('Radiobutton.label',{'sticky':'nswe'})], 'sticky':'nswe'})])
    style.map('TRadiobutton', background=[('selected',p['selected']),('active',p['panel'])], foreground=[('selected',p['accent'])])
    style.configure('TCombobox', fieldbackground=p['panel'], background=p['panel'], foreground=p['text'], arrowcolor=p['text'], padding=6)
    style.map('TCombobox', fieldbackground=[('readonly',p['panel'])], foreground=[('readonly',p['text'])], selectbackground=[('readonly',p['panel'])], selectforeground=[('readonly',p['text'])])
    style.configure('TEntry', fieldbackground=p['panel'], foreground=p['text'], padding=6)
    # Tiny native image elements make a flat, keyboard-accessible ttk slider.
    if not hasattr(window,'scale_icons'):
        window.scale_icons=[]
        for color in ('#329df4','#80c4ff'):
            icon=tk.PhotoImage(master=window,width=16,height=16)
            for y in range(16):
                for x in range(16):
                    if (x-7.5)**2+(y-7.5)**2<=49:icon.put(color,(x,y))
            window.scale_icons.append(icon)
        style.element_create('Precision.slider','image',window.scale_icons[0],('active',window.scale_icons[1]))
    style.layout('Horizontal.TScale',[('Horizontal.Scale.trough',{'sticky':'we','children':[('Precision.slider',{'side':'left','sticky':''})]})])
    style.configure('Horizontal.TScale', background=p['bg'], troughcolor=p['border'], borderwidth=0,lightcolor=p['bg'],darkcolor=p['bg'],bordercolor=p['bg'])
    style.configure('TNotebook', background=p['bg'], borderwidth=0,lightcolor=p['bg'],darkcolor=p['bg'],bordercolor=p['bg'])
    style.layout('TNotebook.Tab', [])
    style.configure('Vertical.TScrollbar', background=p['border'], troughcolor=p['bg'], borderwidth=0, arrowsize=12)
    window.option_add('*TCombobox*Listbox.background', p['panel'])
    window.option_add('*TCombobox*Listbox.foreground', p['text'])
    return p
