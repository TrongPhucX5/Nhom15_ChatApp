
    def add_file_bubble(self, sender, filename, full_path):
        is_me = (sender == "Me" or sender == self.username)
        if is_me:
            bg, align, anchor = BUBBLE_ME, "right", "e"
            txt_col = TEXT_ME
        else:
            bg, align, anchor = BUBBLE_YOU, "left", "w"
            txt_col = TEXT_YOU

        row = ctk.CTkFrame(self.msg_area, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=20)

        if not is_me:
            ctk.CTkButton(row, text=sender[0], width=28, height=28, corner_radius=14, 
                          fg_color=("#e6e8eb", "#333"), text_color="#555", hover=False).pack(side="left", anchor="s", pady=(0,5))

        bubble = ctk.CTkFrame(row, fg_color=bg, corner_radius=18, border_width=1, border_color=("#E4E6EB", "#333"))
        bubble.pack(side=align, anchor=anchor)

        # File Icon + Name
        icon_frame = ctk.CTkFrame(bubble, fg_color="transparent")
        icon_frame.pack(padx=10, pady=5)
        
        ctk.CTkLabel(icon_frame, text="📄", font=("Segoe UI Emoji", 24)).pack(side="left", padx=5)
        
        info_frame = ctk.CTkFrame(icon_frame, fg_color="transparent")
        info_frame.pack(side="left")
        
        ctk.CTkLabel(info_frame, text=filename, font=("Segoe UI", 12, "bold"), text_color=txt_col).pack(anchor="w")
        ctk.CTkLabel(info_frame, text="Đã lưu vào máy", font=("Segoe UI", 10), text_color="gray").pack(anchor="w")
        
        # Open Folder Button
        def open_folder():
             import subprocess
             try:
                subprocess.Popen(f'explorer /select,"{full_path}"')
             except:
                os.startfile(os.path.dirname(full_path))

        ctk.CTkButton(bubble, text="Mở thư mục", width=80, height=24, fg_color=("white", "#444"), text_color=txt_col,
                      command=open_folder).pack(padx=10, pady=(0,10))
