import chardet
import gettext
import json
import os
import webbrowser
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, ttk

#import sys

app_name = 'UV-vis DSP viewer'
app_version = 0.2

lang_dict = {
'en': 'English',
'kk': 'Қазақша',
'ru': 'Русский'
}

def load_file():
    global sample_name, wavelength_list, data_list, peaks_list
    input_filename = filedialog.askopenfilename(filetypes=[('DSP files', '*.dsp')])
    if input_filename:
        wavelength_list, data_list, peaks_list = [], [], []
        refresh_peaks_listbox()
        file_menu.entryconfig(1, state=tk.NORMAL)
        update_plot_btn.config(state=tk.NORMAL)
        with open(input_filename, 'rb') as dsp_file:
            raw_dsp = dsp_file.read()
            file_encoding = chardet.detect(raw_dsp)['encoding']
            dsp_string = raw_dsp.decode(file_encoding).replace('\r', '')
            sample_name, wavelength_list, data_list = parse_dsp_string(dsp_string)
            find_peaks_btn.config(state=tk.NORMAL)
            #print(sys.modules.keys())
            build_plot(wavelength_list, data_list, [])

def parse_dsp_string(dsp_string):
    dsp_lines = dsp_string.split('\n')
    meta_inf_idx = dsp_lines.index('nm')
    sample_filename = dsp_lines[meta_inf_idx-1]
    sample_name = os.path.splitext(sample_filename)[0]
    start_wavelength = int(dsp_lines[meta_inf_idx+1])
    end_wavelength = int(dsp_lines[meta_inf_idx+2])
    step = int(dsp_lines[meta_inf_idx+3])
    if (start_wavelength + end_wavelength) / 2 < config['uv_vis_border']:
        spectrum_type = _('UV')
        conc_signif_stringvar.set(config['uv_default_conc'][0])
        conc_exp_stringvar.set(config['uv_default_conc'][1])
    else:
        spectrum_type = _('visible')
        conc_signif_stringvar.set(config['vis_default_conc'][0])
        conc_exp_stringvar.set(config['vis_default_conc'][1])
    meta_inf_str = f'{sample_filename}:\n{spectrum_type} ({start_wavelength}-{end_wavelength} {nm_label}), step {step} {nm_label}'
    meta_inf_msg.config(text=meta_inf_str)
    data_idx = dsp_lines.index('#DATA')
    data_list = dsp_lines[data_idx+1:]
    data_list = [float(i) for i in data_list if i != '']
    curr_wavelength = start_wavelength
    wavelength_list = []
    for i in data_list:
        wavelength_list.append(curr_wavelength)
        curr_wavelength += step
    return sample_name, wavelength_list, data_list

def generate_y_ticks(data_list):
    y_reserve_coeff = 1.1
    y_range = max(data_list) - min(data_list)
    y_step = 0.5 if y_range < 2 else 1
    ticks_list = [0]
    current_tick = 0
    while current_tick < max(data_list) * y_reserve_coeff:
        current_tick += y_step
        ticks_list.append(current_tick)
    return ticks_list

def build_plot(wavelength_list, data_list, peaks_list):
    global fig
    plt.close() # close existing plot window if exists
    fig, plot_obj = plt.subplots()
    fig.set_size_inches(9.92, 5.22)
    plot_obj.plot(wavelength_list, data_list, '-', linewidth=1, color='black', label=sample_name)
    plot_obj.set_xlim(min(wavelength_list), max(wavelength_list))
    if min(data_list) > 0:
        plot_obj.set_ylim(bottom=0)
    plot_obj.set_xlabel(nm_label)
    plot_obj.set_ylabel('A', rotation='horizontal')
    plot_obj.yaxis.set_label_coords(0,1.02)
    plot_obj.grid(True, which='major')
    plot_obj.grid(True, which='minor', linestyle='--', alpha=0.7)
    y_ticks = generate_y_ticks(data_list)
    plot_obj.set_ylim(top=y_ticks[-1])
    plt.yticks(y_ticks)
    plt.minorticks_on()
    plt.tight_layout()
    plt.legend(loc='best')
    man = plt.get_current_fig_manager()
    man.set_window_title(sample_name)
    if peaks_list:
        peaks_wl, peaks_absorption = zip(*peaks_list)
        plot_obj.plot(peaks_wl, peaks_absorption, 'o', markersize=4, color='red')
    plt.show()

def find_peaks():
    global peaks_list
    peaks_list = []
    positive_diff_count = 0
    positive_diff_thresold = 5
    for idx, elem in enumerate(data_list):
        prev_elem = elem if idx == 0 else data_list[idx-1]
        diff = elem - prev_elem
        if diff > 0:
            positive_diff_count += 1
        if diff < 0 and positive_diff_count > positive_diff_thresold:
            peaks_list.append([wavelength_list[idx-1], data_list[idx-1]])
            positive_diff_count = 0
    refresh_peaks_listbox()

def remove_peak():
    global peaks_list
    if peaks_listbox.curselection():
        selected_peak = peaks_listbox.curselection()[0]
        del peaks_list[selected_peak]
        refresh_peaks_listbox()

def refresh_peaks_listbox():
    peaks_listbox.delete(0, tk.END)
    extinction_text_stringvar.set('')
    if peaks_list:
        for peak in peaks_list:
            peak_str = f'{peak[0]} {nm_label}: {peak[1]}'
            peaks_listbox.insert(tk.END, peak_str)
        remove_peak_btn.config(state=tk.NORMAL)
        calculate_extinction_btn.config(state=tk.NORMAL)
    else:
        remove_peak_btn.config(state=tk.DISABLED)
        calculate_extinction_btn.config(state=tk.DISABLED)

def calculate_extinction():
    if conc_signif_stringvar.get() and conc_exp_stringvar.get():
        conc_significand = float(conc_signif_stringvar.get())
        conc_exponent = int(conc_exp_stringvar.get())
        peaks_substrings = []
        for peak in peaks_list:
            extinction = peak[1] / conc_significand * 10 ** (conc_exponent * -1)
            substring = f'{peak[0]} ({format_float_num(extinction)})'
            peaks_substrings.append(substring)
        peaks_string = f'λ max, {nm_label} (ε): ' + ', '.join(peaks_substrings)
    else:
        peaks_string = _('Enter molar concentration!')
    extinction_text_stringvar.set(peaks_string)

def format_float_num(extinction):
    if round(extinction) == round(extinction, 1):
        extinction = round(extinction)
    else:
        extinction = round(extinction, 1)
    return extinction

def copy_extinction_text():
    root.clipboard_clear()
    root.clipboard_append(extinction_text_stringvar.get())

def save_plot_as(out_format):
    output_filename = filedialog.asksaveasfilename(initialfile=sample_name+out_format)
    if output_filename:
        fig.savefig(output_filename)

def select_language(lang_code):
    config['lang'] = lang_code
    write_config_file()
    t_new = gettext.translation(domain='messages', localedir='locale', languages=[lang_code], fallback=True)
    restart_alert = t_new.gettext('Restart application to switch language!')
    extinction_text_stringvar.set(restart_alert)

def show_settings():
    global uv_vis_entry, uv_entry_1, uv_entry_2, vis_entry_1, vis_entry_2, settings_window
    settings_window = tk.Toplevel()
    settings_window.title(_('Settings'))
    settings_window.geometry('350x250')
    root.eval(f'tk::PlaceWindow {str(settings_window)} center')
    settings_window.columnconfigure(index=0, weight=5)
    for c in range(1,5): settings_window.columnconfigure(index=c, weight=1)
    for r in range(6): settings_window.rowconfigure(index=r, weight=1)
    uv_vis_label_1 = tk.Label(settings_window, text=_('UV-vis border'))
    uv_vis_label_1.grid(row=0, column=0, sticky='w', padx = 10)
    uv_vis_entry = ttk.Entry(settings_window, width=4)
    uv_vis_entry.grid(row=0, column=3)
    uv_vis_entry.insert(0, config['uv_vis_border'])
    uv_vis_label_2 = tk.Label(settings_window, text=nm_label)
    uv_vis_label_2.grid(row=0, column=4, sticky='w', padx = 10)
    default_conc_label = tk.Label(settings_window, text=_('Default sample concentrations:'))
    default_conc_label.grid(row=1, column=0, columnspan=5, sticky='w', padx = 10)
    uv_label_1 = tk.Label(settings_window, text=_('UV'))
    uv_label_1.grid(row=2, column=0, sticky='w', padx = 10)
    uv_entry_1 = ttk.Entry(settings_window, width=4)
    uv_entry_1.grid(row=2, column=1)
    uv_entry_1.insert(0, config['uv_default_conc'][0])
    uv_label_2 = tk.Label(settings_window, text='• 10^')
    uv_label_2.grid(row=2, column=2)
    uv_entry_2 = ttk.Entry(settings_window, width=3)
    uv_entry_2.grid(row=2, column=3)
    uv_entry_2.insert(0, config['uv_default_conc'][1])
    uv_label_3 = tk.Label(settings_window, text=_('mol/L'))
    uv_label_3.grid(row=2, column=4, sticky='w')
    vis_label_1 = tk.Label(settings_window, text=_('visible'))
    vis_label_1.grid(row=3, column=0, sticky='w', padx = 10)
    vis_entry_1 = ttk.Entry(settings_window, width=4)
    vis_entry_1.grid(row=3, column=1)
    vis_entry_1.insert(0, config['vis_default_conc'][0])
    vis_label_2 = tk.Label(settings_window, text='• 10^')
    vis_label_2.grid(row=3, column=2)
    vis_entry_2 = ttk.Entry(settings_window, width=3)
    vis_entry_2.grid(row=3, column=3)
    vis_entry_2.insert(0, config['vis_default_conc'][1])
    vis_label_3 = tk.Label(settings_window, text=_('mol/L'))
    vis_label_3.grid(row=3, column=4, sticky='w')
    reset_btn = tk.Button(settings_window, text='Reset', command=lambda: set_config('default', True) )
    reset_btn.grid(row=5, column=0, sticky='w', padx = 10)
    ok_btn = tk.Button(settings_window, text='OK', command=lambda: set_config('custom', True) )
    ok_btn.grid(row=5, column=4, sticky='e', padx = 10)

def set_config(config_type, close_window):
    global config
    if config_type == 'default':
        config = {
            'lang':             'en',
            'uv_vis_border':    500,     # nm
            'uv_default_conc':  [5, -5], # 5e-5 mol/L
            'vis_default_conc': [1, -2]  # 1e-2 mol/L
        }
    elif config_type == 'custom':
        config['uv_vis_border'] = int(uv_vis_entry.get())
        config['uv_default_conc'][0] = float(uv_entry_1.get())
        config['uv_default_conc'][1] = int(uv_entry_2.get())
        config['vis_default_conc'][0] = float(vis_entry_1.get())
        config['vis_default_conc'][1] = int(vis_entry_2.get())
    write_config_file()
    if close_window:
        settings_window.destroy()

def show_about():
    about_window = tk.Toplevel()
    about_window.title(_('About'))
    about_window.geometry('350x180')
    root.eval(f'tk::PlaceWindow {str(about_window)} center')
    about_window.columnconfigure(index=0, weight=1)
    for r in range(3): about_window.rowconfigure(index=r, weight=1)
    tk.Label(about_window, text=f'{app_name} {app_version}').grid(row=0, sticky='ew')
    about_text = 'matplotlib based viewer for UV-vis spectral data files generated by VISIONlite Scan'
    about_msg = tk.Message(about_window, text=about_text, justify='center', width=288).grid(row=1)
    github_url = 'https://github.com/Fontan030/uv-vis-dsp-viewer'
    github_link = tk.Label(about_window, text=github_url, cursor='hand2', foreground='blue')
    github_link.grid(row=2)
    github_link.bind('<Button-1>', lambda e: webbrowser.open(github_url))

def write_config_file():
    with open('uvdv_config.json', 'w') as settings_file:
        json.dump(config, settings_file)

def close_all_windows():
    plt.close()
    root.destroy()

if os.path.exists('uvdv_config.json'):
    with open('uvdv_config.json', 'r') as settings_file:
        config = json.load(settings_file)
else:
    set_config('default', False)

t = gettext.translation(domain='messages', localedir='locale', languages=[config['lang']], fallback=True)
_ = t.gettext
nm_label = _('nm')

root = tk.Tk()
root.title(app_name)
root.geometry('450x400')
root.eval('tk::PlaceWindow . center')
root.protocol('WM_DELETE_WINDOW', close_all_windows)

root.option_add('*tearOff', tk.FALSE)
file_menu = tk.Menu()
file_menu.add_command(label=_('Open'), command=load_file)
save_as_menu = tk.Menu()
save_as_menu.add_command(label='PNG', command=lambda: save_plot_as('.png') )
save_as_menu.add_command(label='PDF', command=lambda: save_plot_as('.pdf') )
save_as_menu.add_command(label='SVG', command=lambda: save_plot_as('.svg') )
file_menu.add_cascade(label=_('Save plot as'), menu=save_as_menu, state=tk.DISABLED)

edit_menu = tk.Menu()
lang_menu = tk.Menu()
for lang_code, lang_name in lang_dict.items():
    lang_menu.add_command(label=lang_name, command=lambda lc=lang_code: select_language(lc))
edit_menu.add_cascade(label=_('Language'), menu=lang_menu)
edit_menu.add_command(label=_('Settings'), command=show_settings)

help_menu = tk.Menu()
help_menu.add_command(label=_('About'), command=show_about)

main_menu = tk.Menu()
main_menu.add_cascade(label=_('File'), menu=file_menu)
main_menu.add_cascade(label=_('Edit'), menu=edit_menu)
main_menu.add_cascade(label=_('Help'), menu=help_menu)
root.config(menu=main_menu)

root.columnconfigure(index=0, weight=3)
for c in range(1,4): root.columnconfigure(index=c, weight=1)
root.columnconfigure(index=4, weight=3)
for r in range(6): root.rowconfigure(index=r, weight=1)

meta_inf_msg = tk.Message(text=_('Select a .dsp file\n'), width = 384)
meta_inf_msg.grid(row=0, column=0, columnspan=5, sticky='w', padx = 10)

find_peaks_btn = tk.Button(root, text=_('Find peaks'), command=find_peaks, state=tk.DISABLED)
find_peaks_btn.grid(row=1, column=0, sticky='w', padx = 10)

remove_peak_btn = tk.Button(root, text=_('Remove peak'), command=remove_peak, state=tk.DISABLED)
remove_peak_btn.grid(row=1, column=4, sticky='e', padx = 10)

peaks_listbox = tk.Listbox(root, height=5)
peaks_listbox.grid(row=2, column=0, columnspan=5, sticky='ew', padx = 10)

concentration_label_1 = tk.Label(text=_('Molar concentration:'))
concentration_label_1.grid(row=3, column=0)

conc_signif_stringvar = tk.StringVar()
concentration_signif_entry = ttk.Entry(width=4, textvariable=conc_signif_stringvar)
concentration_signif_entry.grid(row=3, column=1)

concentration_label_2 = tk.Label(text='• 10^')
concentration_label_2.grid(row=3, column=2)

conc_exp_stringvar = tk.StringVar()
concentration_exp_entry = ttk.Entry(width=3, textvariable=conc_exp_stringvar)
concentration_exp_entry.grid(row=3, column=3)

concentration_label_3 = tk.Label(text=_('mol/L'))
concentration_label_3.grid(row=3, column=4, sticky='w')

calculate_extinction_btn = tk.Button(root, text=_('Calculate extinction'), command=calculate_extinction,  state=tk.DISABLED)
calculate_extinction_btn.grid(row=4, column=0, sticky='w', padx = 10)

update_plot_btn = tk.Button(root, text=_('Update plot'), command=lambda: build_plot(wavelength_list, data_list, peaks_list), state=tk.DISABLED)
update_plot_btn.grid(row=4, column=4, sticky='e', padx = 10)

extinction_text_stringvar = tk.StringVar()
extinction_text_output = ttk.Entry(textvariable=extinction_text_stringvar)
extinction_text_output.grid(row=5, column=0, columnspan=4, sticky='ew', padx = 10)

copy_btn = tk.Button(root, text=_('Copy'), command=copy_extinction_text)
copy_btn.grid(row=5, column=4, sticky='e', padx = 10)

root.mainloop()