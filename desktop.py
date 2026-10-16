"""CamTether Windows editing interface."""
import os,time,queue,threading
import tkinter as tk
from tkinter import ttk,filedialog,colorchooser,messagebox
from PIL import Image,ImageTk,ImageOps
from effects import DEFAULTS

def show(bridge,port,ips,usb,root,adb_command):
    from windows_dpi import enable_dpi_awareness
    enable_dpi_awareness()
    fx=bridge.effects
    window=tk.Tk();window.title('CamTether · USB camera & editor')
    dpi_scale = window.winfo_fpixels('1i') / 96
    px = lambda value: round(value * dpi_scale)
    window.geometry(f'{min(px(1190),window.winfo_screenwidth()-40)}x{min(px(800),window.winfo_screenheight()-80)}')
    window.minsize(px(980),px(700));window.configure(bg='#10171b')
    style=ttk.Style(window);style.theme_use('clam')
    style.configure('TFrame',background='#10171b');style.configure('TLabel',background='#10171b',foreground='#eaf1ed',font=('Segoe UI',10))
    style.configure('TNotebook',background='#10171b');style.configure('TNotebook.Tab',padding=(12,9))
    style.configure('TButton',padding=(10,7));style.configure('TCheckbutton',background='#10171b',foreground='#eaf1ed')
    header=ttk.Frame(window,padding=(22,18));header.pack(fill='x')
    ttk.Label(header,text='CAMTETHER',font=('Segoe UI',20,'bold')).pack(side='left')
    ttk.Label(header,text='USB camera · Edit your video here',foreground='#9be9b5').pack(side='left',padx=20)
    body=ttk.Frame(window,padding=(20,0));body.pack(fill='both',expand=True)
    right=ttk.Frame(body,width=px(350));right.pack(side='right',fill='y',padx=(16,0));right.pack_propagate(False)
    left=ttk.Frame(body);left.pack(side='left',fill='both',expand=True)
    preview=tk.Label(left,bg='#060a0c',fg='#b8c9c1',text='Waiting for your phone…',font=('Segoe UI',15));preview.pack(fill='both',expand=True)
    stream_status=ttk.Label(left,text='Waiting for camera');stream_status.pack(anchor='w',pady=(12,6))
    effect_status=ttk.Label(left,text='',wraplength=px(680));effect_status.pack(anchor='w',pady=(0,12))
    notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True)
    tabs={}
    for name in ['Crop','Angle','Adjust','Background','Connect']:
        tabs[name]=ttk.Frame(notebook,padding=14);notebook.add(tabs[name],text=name)
    settings,_=fx.snapshot();variables={};pending=[None]
    def save():
        pending[0]=None
        try:fx.save()
        except OSError as e:effect_status.configure(text='Could not save settings: '+str(e))
    def changed(key,value):
        if key in ('keystone_v','keystone_h','level') and 'auto_keystone' in variables:
            variables['auto_keystone'].set(False);fx.set(auto_keystone=False)
        fx.set(**{key:value})
        if pending[0]:window.after_cancel(pending[0])
        pending[0]=window.after(250,save)
    def slider(tab,key,title,low,high):
        row=ttk.Frame(tab);row.pack(fill='x',pady=(7,0))
        ttk.Label(row,text=title).pack(side='left')
        val=ttk.Label(row,text=f'{settings[key]:.2f}');val.pack(side='right')
        var=tk.DoubleVar(value=settings[key]);variables[key]=var
        def slide(value):
            val.configure(text=f'{float(value):.2f}');changed(key,float(value))
        ttk.Scale(tab,from_=low,to=high,variable=var,command=slide).pack(fill='x',pady=(3,1))
    crop=tabs['Crop']
    ttk.Label(crop,text='Frame your shot',font=('Segoe UI',13,'bold')).pack(anchor='w')
    framing=tk.StringVar(value=settings['framing']);variables['framing']=framing
    frame_box=ttk.Combobox(crop,textvariable=framing,values=['Fit entire image','Fill frame'],state='readonly')
    frame_box.pack(fill='x',pady=8);frame_box.bind('<<ComboboxSelected>>',lambda e:changed('framing',framing.get()))
    for key,title,lo,hi in [('zoom','Zoom',1,3),('pan_x','Horizontal position',-1,1),('pan_y','Vertical position',-1,1),('left','Crop left (%)',0,40),('right','Crop right (%)',0,40),('top','Crop top (%)',0,40),('bottom','Crop bottom (%)',0,40)]:slider(crop,key,title,lo,hi)
    ttk.Label(crop,text='Fill frame removes bars by cropping. Position shifts that crop. A sideways phone gives the widest, sharpest shot.',wraplength=px(300)).pack(anchor='w',pady=10)
    angle=tabs['Angle']
    ttk.Label(angle,text='Stand / keystone correction',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(0,10))
    automatic=tk.BooleanVar(value=settings['auto_keystone']);variables['auto_keystone']=automatic
    ttk.Checkbutton(angle,text='Automatic vertical keystone',variable=automatic,
                    command=lambda:changed('auto_keystone',automatic.get())).pack(anchor='w',pady=5)
    auto_status=ttk.Label(angle,text='Auto keystone: waiting',wraplength=px(285));auto_status.pack(fill='x',pady=5)
    def recalibrate():
        automatic.set(True);changed('auto_keystone',True);fx.recalibrate()
    ttk.Button(angle,text='Recalibrate from current room',command=recalibrate).pack(fill='x',pady=5)
    for key,title,lo,hi in [('keystone_v','Vertical perspective',-.25,.25),('keystone_h','Horizontal perspective',-.25,.25),('level','Level / roll (degrees)',-12,12)]:slider(angle,key,title,lo,hi)
    def reset_angle():
        for key in ['keystone_v','keystone_h','level']:variables[key].set(0);changed(key,0.)
    ttk.Button(angle,text='Reset perspective only',command=reset_angle).pack(fill='x')
    ttk.Label(angle,text='Auto checks long room lines on both sides, then locks a mild correction. If uncertain, it leaves the image unchanged. Moving a manual slider turns auto off. Keystone still changes proportions; it cannot recreate eye level.',wraplength=px(290)).pack(anchor='w',pady=15)
    adjust=tabs['Adjust']
    mirror=tk.BooleanVar(value=settings['mirror']);variables['mirror']=mirror
    ttk.Checkbutton(adjust,text='Mirror video',variable=mirror,command=lambda:changed('mirror',mirror.get())).pack(anchor='w',pady=8)
    ttk.Label(adjust,text='Rotate clockwise').pack(anchor='w',pady=(12,6))
    rotation=tk.StringVar(value=str(settings['rotation']));variables['rotation']=rotation
    rotation_box=ttk.Combobox(adjust,textvariable=rotation,values=['0','90','180','270'],state='readonly')
    rotation_box.pack(fill='x');rotation_box.bind('<<ComboboxSelected>>',lambda e:changed('rotation',int(rotation.get())))
    for key,title,lo,hi in [('brightness','Brightness',.4,1.8),('contrast','Contrast',.4,1.8),('saturation','Color intensity',0,2)]:slider(adjust,key,title,lo,hi)
    def reset_edits():
        keys=['zoom','pan_x','pan_y','left','right','top','bottom','rotation','mirror','brightness','contrast','saturation']
        for key in keys:
            variables[key].set(DEFAULTS[key]);changed(key,DEFAULTS[key])
    ttk.Button(adjust,text='Reset crop & adjustments',command=reset_edits).pack(fill='x',pady=20)
    bg=tabs['Background'];mode=tk.StringVar(value=settings['background']);variables['background']=mode
    ttk.Label(bg,text='Your background',font=('Segoe UI',13,'bold')).pack(anchor='w',pady=(0,10))
    modes=ttk.Combobox(bg,textvariable=mode,values=['Original','Blur','Remove / plain color','Image'],state='readonly');modes.pack(fill='x')
    modes.bind('<<ComboboxSelected>>',lambda e:changed('background',mode.get()))
    thumb=ttk.Label(bg,text='No background image chosen',wraplength=px(280));thumb.pack(pady=12)
    def refresh_thumb():
        if fx.background_image is not None:
            thumb.picture=ImageTk.PhotoImage(ImageOps.fit(fx.background_image,(276,155)))
            thumb.configure(image=thumb.picture,text='')
    def choose_image():
        path=filedialog.askopenfilename(title='Choose a background',filetypes=[('Images','*.png *.jpg *.jpeg *.webp *.bmp')])
        if path:
            try:fx.choose_background(path);mode.set('Image');refresh_thumb()
            except Exception as e:messagebox.showerror('Background image',str(e))
    ttk.Button(bg,text='Choose background image…',command=choose_image).pack(fill='x')
    def choose_color():
        color=colorchooser.askcolor(color=fx.snapshot()[0]['color'],title='Background color')[1]
        if color:changed('color',color);mode.set('Remove / plain color');changed('background',mode.get())
    ttk.Button(bg,text='Choose plain color…',command=choose_color).pack(fill='x',pady=8)
    slider(bg,'blur','Blur strength',4,36);slider(bg,'edge','Foreground cutoff',.25,.75)
    ttk.Label(bg,text='Saved automatically. Your chosen image is copied into CamTether, so it is remembered even if the original file moves.\n\nRemoval uses a local model. Hair and fast movement may show imperfect edges. Webcam output uses an opaque background.',wraplength=px(300)).pack(anchor='w',pady=12)
    refresh_thumb()
    connect=tabs['Connect'];address=tk.StringVar(value=ips[0]);link=tk.StringVar()
    ttk.Label(connect,text='Direct USB' if usb else 'Network connection',font=('Segoe UI',13,'bold')).pack(anchor='w')
    ttk.Label(connect,text='Keep USB debugging enabled and the cable connected. Tap Start camera on the phone. Keep the page visible.' if usb else 'Select the connected adapter and scan the pairing QR code.',wraplength=px(295)).pack(anchor='w',pady=12)
    combo=ttk.Combobox(connect,textvariable=address,values=ips,state='readonly');combo.pack(fill='x')
    qr=ttk.Label(connect);qr.pack(pady=12)
    ttk.Entry(connect,textvariable=link,state='readonly').pack(fill='x')
    def pairing(*args):
        import qrcode
        link.set(f'{"http" if usb else "https"}://{address.get()}:{port}/?session={bridge.token[:8]}#token={bridge.token}')
        qr.picture=ImageTk.PhotoImage(qrcode.make(link.get()).convert('RGB').resize((230,230),Image.Resampling.NEAREST));qr.configure(image=qr.picture)
    pairing();combo.bind('<<ComboboxSelected>>',pairing)
    phone_events=queue.SimpleQueue()
    launch_status=ttk.Label(header,text='',foreground='#9be9b5')
    launch_status.pack(side='right',padx=10)
    def wake_start():
        wake_button.configure(state='disabled')
        launch_status.configure(text='Waking phone…')
        url=link.get()
        def work():
            try:
                from phone_control import wake_and_start
                wake_and_start(adb_command,port,url)
                phone_events.put((True,'Start requested · unlock/allow camera on phone if asked'))
            except Exception as error:phone_events.put((False,str(error)))
        threading.Thread(target=work,daemon=True).start()
    if usb:
        wake_button=ttk.Button(header,text='Wake phone & start camera',command=wake_start)
        wake_button.pack(side='right')
    def open_phone():
        try:
            adb_command('reverse',f'tcp:{port}',f'tcp:{port}')
            adb_command('shell','am','start','-a','android.intent.action.VIEW','-d',"'"+link.get()+"'",'-p','com.android.chrome')
        except Exception as e:messagebox.showerror('USB connection',str(e))
    if usb:ttk.Button(connect,text='Open camera page on phone',command=open_phone).pack(fill='x',pady=8)
    def copy():window.clipboard_clear();window.clipboard_append(link.get())
    ttk.Button(connect,text='Copy pairing link',command=copy).pack(fill='x',pady=5)
    def disconnect():bridge.rotate_pairing();pairing()
    ttk.Button(connect,text='Disconnect / new pairing',command=disconnect).pack(fill='x',pady=5)
    footer=ttk.Frame(window,padding=(20,14));footer.pack(fill='x')
    driver=ttk.Label(footer,text='',wraplength=px(760));driver.pack(side='left')
    ttk.Button(footer,text='Set up webcam driver',command=lambda:__import__('webbrowser').open('https://obsproject.com/download')).pack(side='right')
    ttk.Label(window,text='Edits and background are remembered automatically. Video stays on this laptop.',foreground='#93a79e').pack(pady=(0,10))
    previous=[None];ticks=[0];last_preview=[0.]
    def tick():
        while not phone_events.empty():
            ok,message=phone_events.get()
            wake_button.configure(state='normal')
            launch_status.configure(text=message if ok else 'Phone connection failed')
            if not ok:messagebox.showerror('Wake phone & start camera',message)
        frame=bridge.current();marker=(fx.output_id,preview.winfo_width(),preview.winfo_height()) if frame is not None else None
        now=time.monotonic()
        if window.state()!='iconic' and window.winfo_viewable() and now-last_preview[0]>=.1 and marker!=previous[0]:
            last_preview[0]=now
            if frame is None:preview.configure(image='',text='Waiting for your phone…')
            else:
                size=(max(100,preview.winfo_width()-4),max(100,preview.winfo_height()-4))
                preview.picture=ImageTk.PhotoImage(ImageOps.contain(Image.fromarray(frame),size))
                preview.configure(image=preview.picture,text='')
            previous[0]=marker
        ticks[0]+=1
        if ticks[0]%10==0:
            stream_status.configure(text=(f'LIVE · {fx.fps:.0f} processed fps · {bridge.count} frames received' if frame is not None else 'Waiting · tap Start camera on your phone'))
            effect_status.configure(text=fx.status)
            auto_status.configure(text=fx.auto_status)
            driver.configure(text=bridge.driver_status,foreground='#9be9b5' if bridge.driver_ready else '#ffc58a')
        window.after(33,tick)
    def close():
        save();bridge.closed.set();window.destroy()
    window.protocol('WM_DELETE_WINDOW',close);tick()
    if usb:window.after(500,open_phone)
    window.mainloop()
