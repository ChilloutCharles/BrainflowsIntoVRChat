import os
import mne
import numpy as np
import time
import pywt

from multiprocess import Pool
import scipy.signal

if __name__ == '__main__':
    start_time = time.time()

    p = Pool(20)

    def find_edf_files(directory):
        edf_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".edf"):
                    edf_files.append(os.path.join(root, file))
        return edf_files

    datadir = "dataset"
    paths = find_edf_files(datadir)
    raw_list = list(p.map(mne.io.read_raw_edf, paths))

    def get_windows(raw):
        raw.load_data()
        
        # preprocessing
        raw.notch_filter(freqs=50, method='iir')
        raw.notch_filter(freqs=60, method='iir')
        raw.filter(l_freq=8, h_freq=None)
        
        events, event_id = mne.events_from_annotations(raw)
        if len(event_id) != 3:
            return None
        
        sfreq = raw.info['sfreq'] 

        # Identify T0, T1, T2
        selected_events = events[(events[:, 2] == event_id['T1']) | (events[:, 2] == event_id['T2']) | (events[:, 2] == event_id['T0'])]

        # Create Synthetic Events to get the whole minute
        start_event_sample = selected_events[0, 0]
        synthetic_events = np.array([
            [int(start_event_sample + i * sfreq), 0, 1]  # Each event 1 second apart
            for i in range(60 * 2)
        ])

        # Create epochs around these events
        epochs = mne.Epochs(raw, synthetic_events, tmin=0, tmax=(1.0-1/sfreq), preload=True, baseline=None)

        # Convert epochs to NumPy arrays
        data = epochs.get_data()
        return data

        # dwt_coeffs = []
        # max_coeff_len = int(sfreq // 2)
        # for epoch in data:  # Iterate over epochs
        #     epoch_coeffs = []
        #     for channel in epoch:  # Iterate over channels
        #         coeffs = pywt.wavedec(channel, wavelet='db4', level=4)
        #         coeffs = [scipy.signal.resample(coeff, max_coeff_len) for coeff in coeffs]
        #         epoch_coeffs.append(coeffs)
        #     dwt_coeffs.append(epoch_coeffs)

        # # Convert to NumPy array (optional: depends on downstream needs)
        # return np.array(dwt_coeffs)

    data = list(p.map(get_windows, raw_list))
    data = list(filter(lambda x: x is not None, data))

    # filter out bad data
    window_count = data[0].shape[0]
    sample_count = data[0].shape[-1]
    data = list(filter(lambda d: d.shape[0] == window_count and d.shape[-1] == sample_count, data))
    arr = np.array(data)

    # reshape data
    print(arr.shape)
    # arr = arr.reshape(-1, arr.shape[-3], arr.shape[-2], arr.shape[-1])
    # arr = arr.transpose(0, 3, 1, 2)
    arr = arr.reshape(-1, arr.shape[-2], arr.shape[-1])
    arr = arr.transpose(0, 2, 1)

    with open("dataset.pkl", "wb") as f:
        np.save(f, arr)

    end_time = time.time() - start_time

    print(arr.shape, end_time/60)