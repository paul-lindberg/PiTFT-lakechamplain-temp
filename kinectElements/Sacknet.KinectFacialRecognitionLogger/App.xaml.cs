﻿using System;
using System.Collections.Generic;
using System.Configuration;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;

namespace Sacknet.KinectFacialRecognitionLogger
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        /// <summary>
        /// handles arguments
        /// </summary>
        
        //private void Application_Startup(object sender, StartupEventArgs e)
        //{
        //    MainWindow
        //}

        /// <summary>
        /// Displays stack trace on unhandled exceptions
        /// </summary>
        private void Application_DispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
        {
            MessageBox.Show(e.Exception.ToString(), "Unhandled exception, shutting down... :(");
        }
    }
}
