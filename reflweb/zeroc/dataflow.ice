module Dataflow {
    sequence<string> PathList;
    
    interface Util {
        string get_file_metadata(PathList pathlist);
    };
    interface Calc {
        string calc_single(string template_def, string config, int nodenum, string terminal_id);
    };
};
