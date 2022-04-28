import numpy as np
from . import sort_nicely as sn
import os, time, glob


def readfiles(meta):
    """Reads in the files saved in topdir + inputdir and saves them into a list

    Parameters
    ----------
    meta:   MetaClass
        The metadata object.

    Returns
    -------
    meta:   MetaClass
        The metadata object with added segment_list containing the sorted data fits files.
    """
    meta.segment_list = []
    for fname in os.listdir(meta.inputdir):
        if fname.endswith(meta.suffix + '.fits'):
            meta.segment_list.append(meta.inputdir + fname)
    meta.segment_list = np.array(sn.sort_nicely(meta.segment_list))
    return meta

def trim(data, meta):
    """Removes the edges of the data arrays

    Parameters
    ----------
    data:   DataClass
        The data object.
    meta:   MetaClass
        The metadata object.

    Returns
    -------
    data:   DataClass
        The data object with added subdata arrays with trimmed edges depending on xwindow and ywindow which have been set in the S3 ecf.
    meta:   MetaClass
        The metadata object.
    """
    data.subdata = data.data[:, meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]]
    data.suberr  = data.err[:, meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]]
    data.subdq   = data.dq[:, meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]]
    data.subwave = data.wave[meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]]
    data.subv0   = data.v0[:, meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]]
    meta.subny = meta.ywindow[1] - meta.ywindow[0]
    meta.subnx = meta.xwindow[1] - meta.xwindow[0]
    if hasattr(meta, 'diffmask'):
        # Need to crop diffmask and variance from WFC3 as well
        meta.subdiffmask.append(meta.diffmask[-1][:,meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]])
        data.subvariance = np.copy(data.variance[:, meta.ywindow[0]:meta.ywindow[1], meta.xwindow[0]:meta.xwindow[1]])
        delattr(data, 'variance')

    return data, meta

def check_nans(data, mask, log, name=''):
    """Checks where a data array has NaNs

    Parameters
    ----------
    data:   ndarray
        a data array (e.g. data, err, dq, ...)
    mask:   ndarray
        input mask
    log:    logedit.Logedit
        The open log in which NaNs will be mentioned if existent.
    name:   str, optional
        The name of the data array passed in (e.g. SUBDATA, SUBERR, SUBV0)

    Returns
    -------
    mask:   ndarray
        output mask where 0 will be written where the input data array has NaNs
    """
    num_nans = np.sum(np.isnan(data))
    if num_nans > 0:
        log.writelog(f"  WARNING: {name} has {num_nans} NaNs.  Your subregion may be off the edge of the detector subarray.\n"+
                     "Masking NaN region and continuing, but you should really stop and reconsider your choices.")
        inan = np.where(np.isnan(data))
        #subdata[inan]  = 0
        mask[inan]  = 0
    return mask

def makedirectory(meta, stage, counter=None, **kwargs):
    """Creates a directory for the current stage

    Parameters
    ----------
    meta:   MetaClass
        The metadata object.
    stage:  str
        'S#' string denoting stage number (i.e. 'S3', 'S4')
    counter : int
        The run number if you want to force a particular run number.
        Defaults to None which automatically finds the run number.
    **kwargs

    Returns
    -------
    run:    int
        The run number
    """
    if not hasattr(meta, 'datetime') or meta.datetime is None:
        meta.datetime = time.strftime('%Y-%m-%d')
    datetime = meta.datetime

    # This code allows the input and output files to be stored outside of the Eureka! folder
    rootdir = os.path.join(meta.topdir, *meta.outputdir_raw.split(os.sep))
    if rootdir[-1] != os.sep:
      rootdir += os.sep

    outputdir = rootdir + stage + '_' + datetime + '_' + meta.eventlabel + '_run'

    if counter is None:
        counter = 1
        while os.path.exists(outputdir+str(counter)):
            counter += 1
        outputdir += str(counter)+os.sep
    else:
        outputdir += str(counter)+os.sep

    # Nest the different folders underneath one main folder for this run
    for key, value in kwargs.items():
        outputdir += key+str(value)+'_'

    # Remove trailing _ if present
    if outputdir[-1] == '_':
        outputdir = outputdir[:-1]
    
    # Add trailing slash
    if outputdir[-1] != os.sep:
        outputdir += os.sep

    if not os.path.exists(outputdir):
        try:
            os.makedirs(outputdir)
        except (PermissionError, OSError) as e:
            # Raise a more helpful error message so that users know to update topdir in their ecf file
            raise PermissionError(f'You do not have the permissions to make the folder {outputdir}\n'+
                                  f'Your topdir is currently set to {meta.topdir}, but your user account is called {os.getenv("USER")}.\n'+
                                  f'You likely need to update the topdir setting in your {stage} .ecf file.') from e
    if not os.path.exists(os.path.join(outputdir, "figs")):
        os.makedirs(os.path.join(outputdir, "figs"))

    return counter

def pathdirectory(meta, stage, run, old_datetime=None, **kwargs):
    """Finds the directory for the requested stage, run, and datetime (or old_datetime)

    Parameters
    ----------
    meta:   MetaClass
        The metadata object.
    stage:  str
        'S#' string denoting stage number (i.e. 'S3', 'S4')
    run:    int
        run #, output from makedirectory function
    old_datetime:   str
        The date that a previous run was made (for looking up old data)
    **kwargs

    Returns
    -------
    path:   str
        Directory path for given parameters
    """
    if old_datetime is not None:
        datetime = old_datetime
    else:
        if not hasattr(meta, 'datetime') or meta.datetime is None:
            meta.datetime = time.strftime('%Y-%m-%d')
        datetime = meta.datetime

    # This code allows the input and output files to be stored outside of the Eureka! folder
    rootdir = os.path.join(meta.topdir, *meta.outputdir_raw.split(os.sep))
    if rootdir[-1] != os.sep:
      rootdir += os.sep

    outputdir = rootdir + stage + '_' + datetime + '_' + meta.eventlabel +'_run' + str(run) + os.sep

    for key, value in kwargs.items():
        outputdir += key+str(value)+'_'

    # Remove trailing _ if present
    if outputdir[-1] == '_':
        outputdir = outputdir[:-1]
    
    # Add trailing slash
    if outputdir[-1] != os.sep:
        outputdir += os.sep

    return outputdir

def find_fits(meta):
    '''Locates S1 or S2 output FITS files if unable to find an metadata file.

    Parameters
    ----------
    meta:    MetaClass
        The new meta object for the current stage processing.

    Returns
    -------
    meta:   MetaClass
        The meta object with the updated inputdir pointing to the location of
        the input files to use.

    Notes
    -------
    History:

    - April 25, 2022 Taylor Bell
        Initial version.
    '''
    fnames = glob.glob(meta.inputdir+'*'+meta.suffix + '.fits')
    if len(fnames)==0:
        # There were no rateints files in that folder, so let's see if there are in children folders
        fnames = glob.glob(meta.inputdir+'**'+os.sep+'*'+meta.suffix + '.fits', recursive=True)
        fnames = sn.sort_nicely(fnames)

    if len(fnames)==0:
        # If the code can't find any of the reqested files, raise an error and give a helpful message
        raise AssertionError(f'Unable to find any "{meta.suffix}.fits" files in the inputdir: \n"{meta.inputdir}"!\n'+
                             f'You likely need to change the inputdir in {meta.filename} to point to the folder containing the "{meta.suffix}.fits" files.')

    folders = np.unique([os.sep.join(fname.split(os.sep)[:-1]) for fname in fnames])
    if len(folders)>=1:
        # get the file with the latest modified time
        folder = max(folders, key=os.path.getmtime)

    if len(folders)>1:
        # There may be multiple runs - use the most recent but warn the user
        print(f'WARNING: There are multiple folders containing "{meta.suffix}.fits" files in your inputdir: \n"{meta.inputdir}"\n'
             +f'Using the files in: \n{folder}\n'
              +'and will consider aperture ranges listed there. If this metadata file is not a part\n'
              +'of the run you intended, please provide a more precise folder for the metadata file.')

    meta.inputdir = folder
    meta.inputdir_raw = folder[len(meta.topdir):]

    # Make sure there's a trailing slash at the end of the paths
    if meta.inputdir[-1] != os.sep:
        meta.inputdir += os.sep

    return meta

def get_mad(meta, wave_1d, optspec, wave_min=None, wave_max=None):
    """Computes variation on median absolute deviation (MAD) using ediff1d for 2D data.

    Parameters
    ----------
    meta:   MetaClass
        The metadata object.
    wave_1d:    ndarray
        Wavelength array (nx) with trimmed edges depending on xwindow and ywindow which have been set in the S3 ecf
    optspec:    ndarray
        Optimally extracted spectra, 2D array (time, nx)
    wave_min:   float
        Minimum wavelength for binned lightcurves, as given in the S4 .ecf file
    wave_max:   float
        Maximum wavelength for binned lightcurves, as given in the S4 .ecf file

    Returns:
        Single MAD value in ppm
    """
    optspec = np.ma.masked_invalid(optspec)
    n_int, nx = optspec.shape
    if wave_min is not None:
        iwmin = np.argmin(np.abs(wave_1d-wave_min))
    else:
        iwmin = 0
    if wave_max is not None:
        iwmax = np.argmin(np.abs(wave_1d-wave_max))
    else:
        iwmax = None
    normspec = optspec / np.ma.mean(optspec, axis=0)
    ediff = np.ma.zeros(n_int)
    for m in range(n_int):
        ediff[m] = get_mad_1d(normspec[m],iwmin,iwmax)
    mad = np.ma.mean(ediff)
    return mad

def get_mad_1d(data, ind_min=0, ind_max=-1):
    """Computes variation on median absolute deviation (MAD) using ediff1d for 1D data.

    Parameters
    ----------
    data : ndarray
        The array from which to calculate MAD.
    int_min : int
        Minimum index to consider.
    ind_max : int
        Maximum index to consider (excluding ind_max).

    Returns:
        Single MAD value in ppm
    """
    return 1e6 * np.ma.median(np.ma.abs(np.ma.ediff1d(data[ind_min:ind_max])))
