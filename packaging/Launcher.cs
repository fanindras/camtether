using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Reflection;
[assembly: AssemblyTitle("CamTether")]
[assembly: AssemblyVersion("1.1.2.0")]
class Launcher {
    [STAThread] static int Main() {
        try {
            string root=AppDomain.CurrentDomain.BaseDirectory;
            var start=new ProcessStartInfo(Path.Combine(root,"runtime", "pythonw.exe"), "\""+Path.Combine(root,"launch.py")+"\"");
            start.WorkingDirectory=root;
            start.UseShellExecute=false;
            start.CreateNoWindow=true;
            Process.Start(start);
            return 0;
        } catch(Exception error) {
            MessageBox.Show(error.Message,"CamTether could not start");
            return 1;
        }
    }
}
