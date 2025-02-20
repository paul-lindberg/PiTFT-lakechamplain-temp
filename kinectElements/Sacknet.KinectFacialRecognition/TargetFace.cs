﻿using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Sacknet.KinectFacialRecognition
{
    /// <summary>
    /// Describes a target face for facial recognition
    /// </summary>
    public class TargetFace
    {
        /// <summary>
        /// Gets or sets the key returned when this face is found
        /// </summary>
        public string Key { get; set; }

        /// <summary>
        /// Gets or sets the grayscale, 100x100 target image
        /// </summary>
        public Bitmap Image { get; set; }
    }
    /// <summary>
    /// Describes a user for outputting a profile after facial recognition
    /// </summary>
    public class OutputUser
    {
        /// <summary>
        /// Gets or sets the name of a user
        /// </summary>
        public string Name { get; set; }
    }
}
