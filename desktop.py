"""CamTether Windows editing interface."""
import os,time,queue,threading
import tkinter as tk
from tkinter import ttk,filedialog,colorchooser,messagebox
from PIL import Image,ImageTk,ImageOps
from effects import DEFAULTS
from ui_theme import load_theme,save_theme,apply_theme

def show(bridge,port,ips,usb,root,adb_command):
    from windows_dpi import enable_dpi_awareness
    enable_dpi_awareness()
    fx=bridge.effects
    window=tk.Tk();window.title('CamTether · USB camera & editor')
    dpi_scale = window.winfo_fpixels('1i') / 96
    px = lambda value: round(value * dpi_scale)
    window.geometry(f'{min(px(1190),window.winfo_screenwidth()-40)}x{min(px(800),window.winfo_screenheight()-80)}')
    window.minsize(px(980),px(650))
    style=ttk.Style(window);style.theme_use('clam')
    theme=tk.StringVar(value=load_theme(fx.storage))
    palette=apply_theme(style,window,theme.get())
    header=ttk.Frame(window,padding=(22,18));header.pack(fill='x')
    logo_path=root/'branding'/'phone-usb.png'
    if logo_path.exists():
        with Image.open(logo_path) as icon:
            window.logo=ImageTk.PhotoImage(ImageOps.contain(icon.convert('RGBA'),(px(52),px(52))))
        ttk.Label(header,image=window.logo).pack(side='left',padx=(0,10))
        window.iconphoto(True,window.logo)
    ttk.Label(header,text='CamTether',font=('Segoe UI',22,'bold')).pack(side='left')
    ttk.Label(header,text='USB webcam',style='Muted.TLabel').pack(side='left',padx=16)
    theme_bar=ttk.Frame(header);theme_bar.pack(side='right',padx=(14,0))
    body=ttk.Frame(window,padding=(20,0));body.pack(fill='both',expand=True)
    rail=ttk.Frame(body,width=px(134));rail.pack(side='left',fill='y',padx=(0,16));rail.pack_propagate(False)
    right=ttk.Frame(body,width=px(330));right.pack(side='right',fill='y',padx=(20,0));right.pack_propagate(False)
    left=ttk.Frame(body);left.pack(side='left',fill='both',expand=True)
    preview=tk.Label(left,bg=palette['preview'],fg=palette['muted'],text='Connect your phone with USB\n\nWake phone & start camera',font=('Segoe UI',14));preview.pack(fill='both',expand=True)
    output_badge=tk.Label(preview,text=f'{fx.output_size[1]}p  ·  30 fps',bg='#17212d',fg='white',font=('Segoe UI',11,'bold'),padx=12,pady=7)
    output_badge.place(relx=1,x=-12,y=12,anchor='ne')
    preview_info=ttk.Frame(left,padding=(12,12),style='Panel.TFrame');preview_info.pack(fill='x',pady=(12,0))
    stream_status=ttk.Label(preview_info,text='Waiting for camera',style='Status.TLabel');stream_status.pack(anchor='w')
    effect_status=ttk.Label(preview_info,text='',style='Status.TLabel');effect_status.pack(anchor='w',pady=(6,0))
    preview_info.bind('<Configure>',lambda e:effect_status.configure(wraplength=max(100,e.width-px(24))))
    notebook=ttk.Notebook(right);notebook.pack(fill='both',expand=True)
    tabs={}
    canvases=[];nav_buttons={}
    def select_panel(name):
        notebook.select(list(tabs).index(name))
        for key,button in nav_buttons.items():
            button.configure(style='Selected.Nav.TButton' if key==name else 'Nav.TButton')
    for name,label in [('Crop','Frame'),('Angle','Perspective'),('Adjust','Adjust'),('Background','Background'),('Connect','Connect')]:
        page=ttk.Frame(notebook);notebook.add(page,text=label)
        canvas=tk.Canvas(page,highlightthickness=0,bg=palette['bg'],width=px(300))
        scroll=ttk.Scrollbar(page,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas,padding=(8,10,14,16));item=canvas.create_window(0,0,anchor='nw',window=content)
        content.bind('<Configure>',lambda e,c=canvas:c.configure(scrollregion=c.bbox('all')))
        canvas.bind('<Configure>',lambda e,c=canvas,i=item:c.itemconfigure(i,width=e.width))
        tabs[name]=content;canvases.append(canvas)
        button=ttk.Button(rail,text=label,style='Nav.TButton',command=lambda n=name:select_panel(n))
        button.pack(fill='x',pady=3);nav_buttons[name]=button
    select_panel('Crop')
    def theme_changed():
        nonlocal palette
        palette=apply_theme(style,window,theme.get())
        preview.configure(bg=palette['preview'],fg=palette['muted'])
        for canvas in canvases:canvas.configure(bg=palette['bg'])
        try:save_theme(fx.storage,theme.get())
        except OSError as error:messagebox.showerror('Save appearance',str(error))
    for value,label in [('light','Light'),('dark','Dark')]:
        ttk.Radiobutton(theme_bar,text=label,variable=theme,value=value,command=theme_changed).pack(side='left')
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
    ttk.Label(crop,text='Frame',font=('Segoe UI',17,'bold')).pack(anchor='w',pady=(0,12))
    from video_quality import PROFILES, load_quality, save_quality
    ttk.Label(crop,text='Video quality').pack(anchor='w')
    quality=tk.StringVar(value=load_quality(fx.storage))
    quality_box=ttk.Combobox(crop,textvariable=quality,values=list(PROFILES),state='readonly')
    quality_box.pack(fill='x',pady=(6,4))
    quality_note=ttk.Label(crop,text='30 fps target · applies while CamTether stays open',style='Help.TLabel',wraplength=px(285))
    quality_note.pack(fill='x',pady=(0,8))
    def select_quality(event=None):
        try:
            bridge.set_quality(quality.get())
            quality_note.configure(text=f'Applying {quality.get()}... A short video pause is normal. Some meeting apps retain their negotiated size until you reselect the camera.')
        except OSError as error:messagebox.showerror('Save video quality',str(error))
    quality_box.bind('<<ComboboxSelected>>',select_quality)
    ttk.Button(crop,text='Performance & optimization',command=lambda:messagebox.showinfo('Performance & optimization',
        'GPU shows the busiest engine across this Device, including other apps. CamTether currently processes effects on the CPU.\n\n'
        'For 30 fps, processing should stay below 33 ms per frame. Close unused GPU-heavy apps; avoid applying background effects in both CamTether and your meeting app. Hide the preview to save display work without changing output quality.\n\n'
        '1080p needs a phone that supplies enough detail and a Device that sustains 30 fps. Output resolution does not guarantee source detail. If lag remains, choose 720p or 540p yourself; CamTether never automatically reduces quality.')).pack(fill='x',pady=(0,12))
    ttk.Label(crop,text='Higher resolution uses more CPU, memory and USB bandwidth. Your meeting app may also use more GPU.',style='Help.TLabel',wraplength=px(285)).pack(fill='x',pady=(0,12))
    framing=tk.StringVar(value=settings['framing']);variables['framing']=framing
    frame_modes=ttk.Frame(crop);frame_modes.pack(fill='x',pady=8)
    for value,label in [('Fit entire image','Fit'),('Fill frame','Fill')]:
        ttk.Radiobutton(frame_modes,text=label,variable=framing,value=value,command=lambda:changed('framing',framing.get())).pack(side='left',expand=True,fill='x')
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
    ttk.Label(adjust,text='Anti-flicker lighting').pack(anchor='w')
    lighting=tk.StringVar(value=bridge.lighting)
    lighting_box=ttk.Combobox(adjust,textvariable=lighting,values=['Auto','50 Hz','60 Hz'],state='readonly')
    lighting_box.pack(fill='x',pady=(6,6))
    lighting_box.bind('<<ComboboxSelected>>',lambda event:bridge.set_lighting(lighting.get()))
    lighting_status=ttk.Label(adjust,text='Connect the phone to check support.',style='Help.TLabel',wraplength=px(285))
    lighting_status.pack(fill='x',pady=(0,8))
    ttk.Label(adjust,text='50/60 Hz uses a matching manual exposure when supported. It may change brightness. Some LED/PWM lights can still flicker. Auto restores automatic exposure.',style='Help.TLabel',wraplength=px(285)).pack(fill='x',pady=(0,12))
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
    ttk.Label(connect,text='Keep USB debugging enabled and the cable connected. Use Start phone camera above. Unlock or approve camera access on the phone only if Android asks. Keep the camera page visible.' if usb else 'Select the connected adapter and scan the pairing QR code.',wraplength=px(295)).pack(anchor='w',pady=12)
    combo=ttk.Combobox(connect,textvariable=address,values=ips,state='readonly');combo.pack(fill='x')
    qr=ttk.Label(connect);qr.pack(pady=12)
    ttk.Entry(connect,textvariable=link,state='readonly').pack(fill='x')
    def pairing(*args):
        import qrcode
        link.set(f'{"http" if usb else "https"}://{address.get()}:{port}/?session={bridge.token[:8]}#token={bridge.token}')
        qr.picture=ImageTk.PhotoImage(qrcode.make(link.get()).convert('RGB').resize((230,230),Image.Resampling.NEAREST));qr.configure(image=qr.picture)
    pairing();combo.bind('<<ComboboxSelected>>',pairing)
    phone_events=queue.SimpleQueue()
    launch_status=ttk.Label(connect,text='',style='Help.TLabel',wraplength=px(285))
    launch_status.pack(fill='x',pady=(12,0))
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
        wake_button=ttk.Button(header,text='Start phone camera',command=wake_start,style='Primary.TButton')
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
    footer=ttk.Frame(window,padding=(22,14),style='Footer.TFrame');footer.pack(fill='x',pady=(16,0))
    footer.columnconfigure(0,weight=1)
    footer.columnconfigure(1,weight=1)
    driver=ttk.Label(footer,text='',style='Footer.TLabel',wraplength=px(500));driver.grid(row=0,column=0,sticky='w')
    gpu_label=ttk.Label(footer,text='GPU - measuring...',style='Footer.TLabel');gpu_label.grid(row=0,column=1,sticky='e')
    ttk.Label(footer,text='Settings saved automatically',style='Footer.TLabel').grid(row=1,column=0,sticky='w',pady=(8,0))
    ttk.Label(footer,text='Video stays on this Device',style='Footer.TLabel').grid(row=1,column=1,sticky='e',pady=(8,0))
    def remove_camera():
        if messagebox.askokcancel('Remove webcam components', 'Close meeting apps and browsers first. CamTether will close and remove its own webcam files. You can then uninstall CamTether in Windows Settings. Existing OBS installations are preserved.'):
            bridge.remove_camera_files=True
            close()
    ttk.Button(connect,text='Remove webcam components',command=remove_camera).pack(fill='x',pady=(20,5))
    ttk.Label(connect,text='Closing the window keeps CamTether running in the system tray. Right-click its tray icon to open or exit.',style='Help.TLabel',wraplength=px(285)).pack(fill='x',pady=(12,0))
    tray=None
    try:
        from system_tray import SystemTray
        tray=SystemTray(window)
    except Exception as error:
        launch_status.configure(text='System tray unavailable: '+str(error))
    from gpu_usage import GpuMonitor
    gpu=GpuMonitor(bridge.closed)
    previous=[None];ticks=[0];last_preview=[0.]
    def tick():
        if tray:
            while not tray.events.empty():
                action=tray.events.get()
                if action=='exit':
                    close();return
                window.deiconify();window.lift();window.focus_force()
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
            stream_status.configure(text=(f'LIVE  ·  {fx.fps:.0f} fps' if frame is not None else 'Waiting for phone camera'))
            effect_status.configure(text=fx.status.replace('laptop','Device'))
            gpu_label.configure(text=gpu.label)
            active=bridge.active_output_size
            output_badge.configure(text=f'{active[1] if active else fx.output_size[1]}p  ·  30 fps'+('  ·  applying' if active and active!=fx.output_size else ''))
            info=bridge.camera_info
            lighting_status.configure(text=info.get('lighting_status','Connect the phone to check support.'))
            if frame is not None:stream_status.configure(text=f'LIVE  ·  {fx.fps:.0f} fps  ·  {fx.processing_ms:.1f} ms processing')
            auto_status.configure(text=fx.auto_status)
            driver.configure(text=bridge.driver_status,foreground=palette['accent'] if bridge.driver_ready else palette['muted'])
        window.after(33 if window.winfo_viewable() else 250,tick)
    def close():
        save();bridge.closed.set()
        if tray:tray.close()
        window.destroy()
    def hide_to_tray():
        save()
        if tray and tray.visible:
            window.withdraw()
        elif messagebox.askokcancel('Exit CamTether', 'The system tray is unavailable. Exit CamTether and stop the camera?'):
            close()
    ttk.Button(connect,text='Exit CamTether',command=close).pack(fill='x',pady=(12,5))
    window.protocol('WM_DELETE_WINDOW',hide_to_tray);tick()
    if usb:launch_status.configure(text='Use Start phone camera above. First use may require permission on the phone.')
    window.mainloop()
