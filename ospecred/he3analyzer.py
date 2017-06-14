import datetime
import time
import os
import pickle

try:
    import simplejson as json
except ImportError:
    import json

from numpy import exp, zeros, float64, vectorize, array, where, empty, linalg

class He3Analyzer:
    """ an object that contains information about a particular 3He cell,
    including initial polarization and transmission and initial time.
    Member functions give polarization efficiency and polarization-correction
    matrix as a function of time """
    default_params = {
            'P0': '1.0',
            'T0': '1.0',
            'Gamma': '300.0',
            'sigmanl': '1.0',
            't0': '0',
            't0_str': '',
            'tf': '0',
            'tf_str': '',
            'Psm': '1.0',
            'Pf': '1.0',
            'name': '',
            'id_num': '1'}

    time_fmt = '%a %b %d %H:%M:%S %Y'

    def __init__(self, params={}):
        """ initialization parameters for cell:
            P0 = polarization at time t0
            T0 = transmission at t0
            Gamma = decay time constant for cell (hours)
            sigmanl = proportional to how much 3He in the beam path
            t0 = reference time (when initial measurements done)
            tf = decommission time (when cell is pulled from experiment)
            Psm = (supermirror + sample) polarization
            Pf = flipper polarization = (2*efficiency - 1) """
        default_params = self.default_params.copy()
        default_params.update(params)
        params = default_params
        self.params = params
        self.P0 = float(params['P0'])
        self.T0 = float(params['T0'])
        self.Gamma = float(params['Gamma'])
        self.sigmanl = float(params['sigmanl'])
        self.t0_str = params['t0_str'] # datetime string, format =  '%a %b %d %H:%M:%S %Y'
        # synchronize timestamp representations
        if self.t0_str == '': # we're working with a timestamp rather than a string time and date
            self.t0 = float(params['t0'])
            self.t0_str = time.ctime(float(params['t0']))
        else: # or we have a formatted date '%a %b %d %H:%M:%S %Y'
            self.t0 = time.mktime(time.strptime(self.t0_str, self.time_fmt))
        self.tf_str = params['tf_str'] # datetime string, format =  '%a %b %d %H:%M:%S %Y'
        if self.tf_str == '': # we're working with a timestamp rather than a string time and date
            self.tf = float(params['tf'])
            self.tf_str = time.ctime(float(params['tf']))
        else: # or we have a formatted date '%a %b %d %H:%M:%S %Y'
            self.tf = time.mktime(time.strptime(self.tf_str, self.time_fmt))
        self.start_datetime = datetime.datetime.strptime(self.t0_str, self.time_fmt)
        self.end_datetime = datetime.datetime.strptime(self.tf_str, self.time_fmt)
        self.Psm = float(params['Psm'])
        self.Pf = float(params['Pf'])
        self.name = params['name']
        self.id_num = int(params['id_num'])

    def __repr__(self):
        repr = self.__class__.__name__ + '('
        repr += json.dumps(self.params, sort_keys=True, indent=4)
        repr += ')'
        return repr

    def isActive(self, ref_datetime):
        return ((ref_datetime <= self.end_datetime) and (ref_datetime >= self.start_datetime))

    def tFromDatetime(self, ref_datetime):
        time_diff = ref_datetime - self.start_datetime
        t = time_diff.days * 86400. + time_diff.seconds # datetime timedelta is an odd duck
        # if python version is >= 2.7, use datetime.timedelta.total_seconds() instead
        return t

    def getPolarization(self, t):
        """ t is the time since t0, in seconds """
        if type(t) == datetime.datetime:
            t = self.tFromDatetime(t)
        Gamma_seconds = self.Gamma * 60. * 60.
        P = self.P0 * exp(-t / Gamma_seconds)
        return P

    def getTransmission(self, t, aligned=True):
        """ returns the transmission of the analyzer for neutrons aligned
        or anti-aligned with analyzer field (3He polarization varies with time) """
        P = self.getPolarization(t)
        if aligned:
            T = self.T0 * exp(-(1.0 - P) * self.sigmanl)
        else:
            T = self.T0 * exp(-(1.0 + P) * self.sigmanl)
        return T

    def getTransmissionVec(self, t, aligned=[True]):
        """ returns the transmission of the analyzer for neutrons aligned
        or anti-aligned with analyzer field (3He polarization varies with time) """
        T = empty(aligned.shape)
        P = self.getPolarization(t)
        T[aligned] = self.T0 * exp(-(1.0 - P) * self.sigmanl)
        T[logical_not(aligned)] = self.T0 * exp(-(1.0 + P) * self.sigmanl)
        return T

    def getNumberIncident(self, aligned=True, flipper_on=False):
        """ corrects for the polarization efficiency of the front-end components (not time-dependent) """
        if aligned:
            if flipper_on:
                N = (1.0 - self.Pf * self.Psm) / 2.0
            else:
                N = (1.0 + self.Psm) / 2.0
        else:
            if flipper_on:
                N = (1.0 + self.Pf * self.Psm) / 2.0
            else:
                N = (1.0 - self.Psm) / 2.0
        return N

    def getNumberIncidentVec(self, front_spin_up=[True], flipper_on=[False]):
        """ corrects for the polarization efficiency of the front-end components (not time-dependent) """
        N = empty(front_spin_up.shape)
        N[logical_and(front_spin_up, flipper_on)] = (1.0 - self.Pf * self.Psm) / 2.0
        N[logical_and(front_spin_up, logical_not(flipper_on))] = (1.0 + self.Psm) / 2.0
        N[logical_and(logical_not(front_spin_up), flipper_on)] = (1.0 + self.Pf * self.Psm) / 2.0
        N[logical_and(logical_not(front_spin_up), logical_not(flipper_on))] = (1.0 - self.Psm) / 2.0
        return N

    def getNTMatrix(self, t):
        """ creates matrix elements for the polarization-correction
            this assumes the order of elements is Rup-up, Rup-down, Rdown-down, Rdown-up
            and for I: Iup-up, Iup-down, Idown-up, Idown-down   """

        flipper_on = array([
        [False, False, False, False],
        [False, False, False, False],
        [True, True, True, True],
        [True, True, True, True]
        ])
        # front_spin_up: True if neutrons are spin-up arriving at sample
        front_spin_up = array([
        [True, True, False, False],
        [True, True, False, False],
        [True, True, False, False],
        [True, True, False, False]
        ])
        # back_spin_up: True if neutrons are spin-up arriving at detector
        back_spin_up = array([
        [True, False, False, True],
        [True, False, False, True],
        [True, False, False, True],
        [True, False, False, True]
        ])
        # He3_up: True if He3 polarization is normal (not reversed)
        He3_up = array([
        [True, True, True, True],
        [False, False, False, False],
        [True, True, True, True],
        [False, False, False, False]
        ])
        # back_aligned: True if scattered neutron is parallel to 3He polarization
        #back_aligned = array([
        #[True, False, False, True],
        #[False, True, True, False],
        #[True, False, False, True],
        #[False, True, True, False]
        #])
        back_aligned = logical_or(logical_and(back_spin_up, He3_up), logical_and(logical_not(back_spin_up),  logical_not(He3_up)))

        N = self.getNumberIncidentVec(front_spin_up, flipper_on)
        T = self.getTransmissionVec(t, back_aligned)

        return N * T

    def getNTRow(self, t, flipper_on=False, He3_up=True):
        flipper_on = array([flipper_on])
        He3_up = array([He3_up])
        # front_spin_up: True if neutrons are spin-up arriving at sample
        front_spin_up = array([
        [True, True, False, False]
        ])
        # back_spin_up: True if neutrons are spin-up arriving at detector
        back_spin_up = array([
        [True, False, False, True]
        ])
        back_aligned = logical_or(logical_and(back_spin_up, He3_up), logical_and(logical_not(back_spin_up),  logical_not(He3_up)))

        N = self.getNumberIncidentVec(front_spin_up, flipper_on)
        T = self.getTransmissionVec(t, back_aligned)

        NT = N * T

        return N * T

    def getNTMasked(self, t, flipper_on_select=False, He3_up_select=True):
        flipper_on = array([
        [False, False, False, False],
        [False, False, False, False],
        [True, True, True, True],
        [True, True, True, True]
        ])
        # front_spin_up: True if neutrons are spin-up arriving at sample
        front_spin_up = array([
        [True, True, False, False],
        [True, True, False, False],
        [True, True, False, False],
        [True, True, False, False]
        ])
        # back_spin_up: True if neutrons are spin-up arriving at detector
        back_spin_up = array([
        [True, False, False, True],
        [True, False, False, True],
        [True, False, False, True],
        [True, False, False, True]
        ])
        # He3_up: True if He3 polarization is normal (not reversed)
        He3_up = array([
        [True, True, True, True],
        [False, False, False, False],
        [True, True, True, True],
        [False, False, False, False]
        ])

        back_aligned = logical_or(logical_and(back_spin_up, He3_up), logical_and(logical_not(back_spin_up),  logical_not(He3_up)))

        N = self.getNumberIncidentVec(front_spin_up, flipper_on)
        T = self.getTransmissionVec(t, back_aligned)
        NT = zeros((4, 4))
        mask = logical_and((flipper_on == flipper_on_select), (He3_up == He3_up_select))
        print(mask)
        NT[mask] = (N * T)[mask]

        return NT

class He3AnalyzerCollection():
    """
    Holds a collection of defined He3Analyzers,
    with methods for adding more and deleting.

    Also provides all the access methods of single He3Analyzer,
    but with the abstraction that the lookup is determined by
    the absolute timestamp.

    Helper function is getActiveCell(t) which returns active cell for that time.
    """
    def __init__(self, filename='he3cells.json', path=None, cells=[]):
        if path == None: path = os.getcwd()
        self.path = path
        self.cells = cells
        try:
            print("loading %s" % filename)
            self.AddFromFile(filename)
            print("loaded %s" % filename)
        except:
            pass

    def AddFromFile(self, filename='he3cells.json'):
        # function to load up all existing stored He3Cell parameters
        full_fn = os.path.join(self.path, filename)
        all_cells_params = json.load(open(full_fn, 'r'))
        # file should contain a list of dictionaries, one for each cell
        cells = []
        for cell_params in all_cells_params:
            cells.append(He3Analyzer(cell_params))
        self.cells.extend(cells)
        return cells

    def Save(self, filename='he3cells.json'):
        all_cells_params = [cell.params for cell in self.cells]
        full_fn = os.path.join(self.path, filename)
        json.dump(all_cells_params, open(full_fn, 'w'), sort_keys=True, indent=4)

    def AddNew(self, params=None, autosave=True):
        params_out = He3Analyzer.default_params.copy()
        params_out.update(params)
        self.cells.append(He3Analyzer(params_out))
        self.Save()

    def Remove(self, num):
        self.cells.pop(num)
        self.Save()

    def getActiveCell(self, ref_datetime=None):
        """ returns the first He3Analyzer instance from the list
        that is active at time ref_datetime
        """
        if ref_datetime == None:
            ref_datetime = datetime.datetime.now()
        for cell in self.cells:
            if cell.isActive(ref_datetime):
                return cell
        # if we get to this point: there was no hit on any active cell
        return None

    def getPolarization(self, t, *args, **kwargs):
        """ t is the time since t0, in seconds """
        return self.getActiveCell(t).getPolarization(t, *args, **kwargs)

    def getTransmission(self, t, *args, **kwargs):
        """ returns the transmission of the analyzer for neutrons aligned
        or anti-aligned with analyzer field (3He polarization varies with time) """
        return self.getActiveCell(t).getTransmission(t, *args, **kwargs)

    def getTransmissionVec(self, t, *args, **kwargs):
        """ returns the transmission of the analyzer for neutrons aligned
        or anti-aligned with analyzer field (3He polarization varies with time) """
        return self.getActiveCell(t).getTransmissionVec(t, *args, **kwargs)

    def getNumberIncident(self, t, *args, **kwargs):
        """ corrects for the polarization efficiency of the front-end components (not time-dependent) """
        return self.getActiveCell(t).getNumberIncident(t, *args, **kwargs)

    def getNumberIncidentVec(self, t, *args, **kwargs):
        """ corrects for the polarization efficiency of the front-end components (not time-dependent) """
        return self.getActiveCell(t).getNumberIncidentVec(t, *args, **kwargs)

    def getNTMatrix(self, t, *args, **kwargs):
        """ creates matrix elements for the polarization-correction
            this assumes the order of elements is Rup-up, Rup-down, Rdown-down, Rdown-up
            and for I: Iup-up, Iup-down, Idown-up, Idown-down   """
        return self.getActiveCell(t).getNTMatrix(t, *args, **kwargs)

    def getNTRow(self, t, *args, **kwargs):
        return self.getActiveCell(t).getNTRow(t, *args, **kwargs)

    def getNTMasked(self, t, *args, **kwargs):
        return self.getActiveCell(t).getNTMasked(t, *args, **kwargs)

    def dumps(self):
        return pickle.dumps(self)
        #raise NotImplementedError("Write a dumps method for He3AnalyzerCollection")

    @classmethod
    def loads(self, str):
        return pickle.loads(str)
        #raise NotImplementedError("Write a loads method for He3AnalyzerCollection")

    def get_plottable(self):
        return json.dumps({})
        #raise NotImplementedError("Write a get_plottable method for He3AnalyzerCollection")

class wxHe3AnalyzerCollection(He3AnalyzerCollection):
    """ version with wx GUI interaction for AddNew and getActiveCell """

    def __init__(self, filename='he3cells.json', path=None, cells=[]):
        import wx, wx.calendar
        He3AnalyzerCollection.__init__(self, filename='he3cells.json', path=None, cells=[])

    def AddNew(self, params=None, autosave=True):
        params_out = He3Analyzer.default_params.copy()
        params_out.update(params)
        dlg = get_cell_params_dialog(None, -1, 'Get New Cell Parameters', params_out)
        if not dlg.ShowModal() == wx.ID_OK:
            dlg.Destroy()
            return #cancel button pushed
        dlg.Destroy()
        self.cells.append(He3Analyzer(params_out))
        self.Save()

    def getActiveCell(self, ref_datetime=None, popup_on_fail=True):
        """ returns the first He3Analyzer instance from the list
        that is active at time ref_datetime

        if popup_on_fail is True, call the gui to add a cell if
        there is no active cell defined for time ref_datetime """
        if ref_datetime == None:
            ref_datetime = datetime.datetime.now()
        for cell in self.cells:
            if cell.isActive(ref_datetime):
                return cell
        # if we get to this point: there was no hit on any active cell
        if popup_on_fail:
            timestr = ref_datetime.strftime('%a %b %d %H:%M:%S %Y')
            dlg = wx.MessageDialog(None, 'No matching cell found for {time} - create one now?'.format(time=timestr),
                                   'No match',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if not dlg.ShowModal() == wx.ID_YES:
                dlg.Destroy()
                return #cancel button pushed
            dlg.Destroy()
            self.AddNew(params={"t0_str":ref_datetime.ctime()})

"""
class get_cell_params_dialog(wx.Dialog):
    def __init__(self, parent, id, title, params):
        import wx, wx.calendar
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, size=(600, 400), style=wx.DEFAULT_DIALOG_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)

        #-- I think you need a panel if you're going to have more than one control in your frame.
        #panel = wx.Panel(self, -1)
        self.params = params

        #-- Create the processing button, add it to the panel and wire it up to a function in the class
        btn_SaveExit = wx.Button(self, wx.ID_OK, "&Done")
        self.Bind(wx.EVT_BUTTON, self.saveExit, btn_SaveExit)

        #-- Create the close button, add it to the panel and wire it up to a function in the class
        btn_Close = wx.Button(self, -1, "&Cancel")
        self.Bind(wx.EVT_BUTTON, self.onExit, btn_Close)

        #-- Now we have to create a grid to layout our controls
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_time_controls = wx.BoxSizer(wx.HORIZONTAL)
        #rows=4,cols=1,hgap=1,vgap=5)

        sizer_buttons = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        sizer_buttons.Add(btn_SaveExit)
        sizer_buttons.Add(btn_Close)

        sizer_params = wx.FlexGridSizer(rows=20, cols=2, hgap=5, vgap=10)
        self.values = {}
        self.text_labels = {}

        self.keys = [
        'P0',
        'T0',
        'Gamma',
        'sigmanl',
        'Psm',
        'Pf',
        'name',
        'id_num',
        ]

        self.labels = [
        'Initial Polarization (P0): ',
        'Initial Transmission (T0): ',
        'Decay time const. (Gamma, hours): ',
        'Sigma n l : ',
        'Supermirror Polarization (Psm): ',
        'Flipper polarization (Pf): ',
        'Cell name (for reference only): ',
        'Cell id# (integer):',
        ]
        for key, label in zip(self.keys, self.labels):
            value = wx.TextCtrl(self, 1, size=(100, -1))
            text_label = wx.StaticText(self, -1, label)
            self.values[key] = value
            self.text_labels[key] = text_label
            sizer_params.Add(text_label)
            sizer_params.Add(value)
            value.SetValue(str(params[key]))

        #self.filenames = params['inFileNames']
        ###############################################
        # Set initialization time for cell (t0):
        ###############################################
        self.static_line_1 = wx.StaticLine(self, -1)
        self.time_label_0 = wx.StaticText(self, -1, "Select t0 (cell initial characterization)")
        self.calendar_ctrl_0 = wx.calendar.CalendarCtrl(self, -1)
        self.spin_ctrl_hour_0 = wx.SpinCtrl(self, -1, "", min=0, max=23)
        self.label_hour_0 = wx.StaticText(self, -1, "Hour")
        self.spin_ctrl_minute_0 = wx.SpinCtrl(self, -1, "", min=0, max=60)
        self.label_minute_0 = wx.StaticText(self, -1, "Minute")

        try:
            t0 = datetime.datetime.strptime(params['t0_str'], '%a %b %d %H:%M:%S %Y')
        except:
            t0 = datetime.datetime.now()

        self.spin_ctrl_hour_0.SetValue(t0.hour)
        self.spin_ctrl_minute_0.SetValue(t0.minute)
        wxDate_0 = wx.DateTime()
        wxDate_0.Set(year=t0.year, month=t0.month - 1, day=t0.day)
        self.calendar_ctrl_0.SetDate(wxDate_0)

        ###############################################
        # Set decommissioning time for cell (tf):
        ###############################################
        self.static_line_2 = wx.StaticLine(self, -1)
        self.time_label_f = wx.StaticText(self, -1, "Select tf (cell decomissioning time)")
        self.calendar_ctrl_f = wx.calendar.CalendarCtrl(self, -1)
        self.spin_ctrl_hour_f = wx.SpinCtrl(self, -1, "", min=0, max=23)
        self.label_hour_f = wx.StaticText(self, -1, "Hour")
        self.spin_ctrl_minute_f = wx.SpinCtrl(self, -1, "", min=0, max=60)
        self.label_minute_f = wx.StaticText(self, -1, "Minute")

        try:
            tf = datetime.datetime.strptime(params['tf_str'], '%a %b %d %H:%M:%S %Y')
        except:
            tf = datetime.datetime.now()

        self.spin_ctrl_hour_f.SetValue(tf.hour)
        self.spin_ctrl_minute_f.SetValue(tf.minute)
        wxDate_f = wx.DateTime()
        wxDate_f.Set(year=tf.year, month=tf.month - 1, day=tf.day)
        self.calendar_ctrl_f.SetDate(wxDate_f)


        sizer_t0_ctrl = wx.BoxSizer(wx.VERTICAL)
        sizer_hm_0 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_minute_0 = wx.BoxSizer(wx.VERTICAL)
        sizer_hour_0 = wx.BoxSizer(wx.VERTICAL)
        sizer_hour_0.Add(self.spin_ctrl_hour_0)
        sizer_hour_0.Add(self.label_hour_0)
        sizer_hm_0.Add(sizer_hour_0)
        sizer_minute_0.Add(self.spin_ctrl_minute_0)
        sizer_minute_0.Add(self.label_minute_0)
        sizer_hm_0.Add(sizer_minute_0)
        sizer_t0_ctrl.Add(self.static_line_1, flag=wx.EXPAND)
        sizer_t0_ctrl.Add(self.time_label_0)
        sizer_t0_ctrl.Add(sizer_hm_0)
        sizer_t0_ctrl.Add(self.calendar_ctrl_0)

        sizer_tf_ctrl = wx.BoxSizer(wx.VERTICAL)
        sizer_hm_f = wx.BoxSizer(wx.HORIZONTAL)
        sizer_minute_f = wx.BoxSizer(wx.VERTICAL)
        sizer_hour_f = wx.BoxSizer(wx.VERTICAL)
        sizer_hour_f.Add(self.spin_ctrl_hour_f)
        sizer_hour_f.Add(self.label_hour_f)
        sizer_hm_f.Add(sizer_hour_f)
        sizer_minute_f.Add(self.spin_ctrl_minute_f)
        sizer_minute_f.Add(self.label_minute_f)
        sizer_hm_f.Add(sizer_minute_f)
        sizer_tf_ctrl.Add(self.static_line_2, flag=wx.EXPAND)
        sizer_tf_ctrl.Add(self.time_label_f)
        sizer_tf_ctrl.Add(sizer_hm_f)
        sizer_tf_ctrl.Add(self.calendar_ctrl_f)

        sizer_time_controls.Add(sizer_t0_ctrl)
        sizer_time_controls.Add((20, 20), 0, 0, 0)
        sizer_time_controls.Add(sizer_tf_ctrl)
        sizer_main.Add(sizer_params)
        sizer_main.Add(sizer_time_controls)
        #sizer_main.Add(sizer_t0_ctrl)
        #sizer_main.Add(sizer_tf_ctrl)
        sizer_main.Add(sizer_buttons)

        self.SetSizer(sizer_main)
        sizer_main.Fit(self)

        #-- Show the window that we've just built

    def saveExit(self, event):
        for key in self.keys:
            self.params[key] = self.values[key].GetValue()
        wxDate = self.calendar_ctrl_0.GetDate() # have to convert to datetime
        t0 = datetime.datetime(wxDate.GetYear(), wxDate.GetMonth() + 1, wxDate.GetDay(), self.spin_ctrl_hour_0.GetValue(), self.spin_ctrl_minute_0.GetValue())
        self.params['t0_str'] = t0.ctime()
        wxDate = self.calendar_ctrl_f.GetDate() # have to convert to datetime
        tf = datetime.datetime(wxDate.GetYear(), wxDate.GetMonth() + 1, wxDate.GetDay(), self.spin_ctrl_hour_f.GetValue(), self.spin_ctrl_minute_f.GetValue())
        self.params['tf_str'] = tf.ctime()
        self.EndModal(wx.ID_OK)
        #self.Close(True)

    def onExit(self, event):
        self.Close(True)

"""
