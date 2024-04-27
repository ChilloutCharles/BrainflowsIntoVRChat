import argparse
import time
import pickle
import os

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

WINDOW_SECONDS = 7
BUFFER_SECONDS = 1
SAVE_FILENAME = 'recorded_eeg'
SAVE_EXTENSION = '.pkl'

def main():
    parser = argparse.ArgumentParser()
    # use docs to check which parameters are required for specific board, e.g. for Cyton - set serial port
    parser.add_argument('--timeout',        type=int, required=False, default=0,  help='timeout for device discovery or connection')
    parser.add_argument('--ip-port',        type=int, required=False, default=0,  help='ip port')
    parser.add_argument('--ip-protocol',    type=int, required=False, default=0,  help='ip protocol, check IpProtocolType enum')
    parser.add_argument('--ip-address',     type=str, required=False, default='', help='ip address')
    parser.add_argument('--serial-port',    type=str, required=False, default='', help='serial port')
    parser.add_argument('--mac-address',    type=str, required=False, default='', help='mac address')
    parser.add_argument('--other-info',     type=str, required=False, default='', help='other info')
    parser.add_argument('--serial-number',  type=str, required=False, default='', help='serial number')
    parser.add_argument('--file',           type=str, required=False, default='', help='file',)
    parser.add_argument('--actions',        type=int, required=True,              help='number of actions to record')
    parser.add_argument('--sessions',       type=int, required=False, default=2,  help='number of sessions per action to record')
    parser.add_argument('--overwrite',      type=int, required=False, default=1,  help='1 to overwrite/remove old recordings, 0 to add results as an additional data file')
    parser.add_argument('--board-id',       type=str, required=True,              help='board id or name, check docs to get a list of supported boards. mu_02 is MUSE_2016_BOARD')
    args = parser.parse_args()

    params               = BrainFlowInputParams()
    params.ip_port       = args.ip_port
    params.serial_port   = args.serial_port
    params.mac_address   = args.mac_address
    params.other_info    = args.other_info
    params.serial_number = args.serial_number
    params.ip_address    = args.ip_address
    params.ip_protocol   = args.ip_protocol
    params.timeout       = args.timeout
    params.file          = args.file

    action_count = args.actions
    session_count = args.sessions
    
    doOverwrite = True if args.overwrite == 1 else False

    ### Board Id selection ###
    try:
        master_board_id = int(args.board_id)
    except ValueError:
        master_board_id = BoardIds[args.board_id.upper()]

    board = BoardShim(master_board_id, params)

    sampling_rate = BoardShim.get_sampling_rate(master_board_id)
    sampling_size = sampling_rate * WINDOW_SECONDS

    action_dict = {action_idx:[] for action_idx in range(action_count)}
    record_data = {
        "board_id" : master_board_id,
        "window_seconds" : WINDOW_SECONDS
    }

    board.prepare_session()
    board.start_stream()

    # 1. wait 5 seconds before starting
    wait_seconds = 2
    print("Get ready in {} seconds".format(wait_seconds))
    time.sleep(wait_seconds)

    for _ in range(session_count):
        for i in action_dict:
            input("Ready to record action {}. Press enter to continue".format(i))
            print("Think Action {} for {} seconds".format(i, WINDOW_SECONDS + BUFFER_SECONDS))
            time.sleep(WINDOW_SECONDS + BUFFER_SECONDS)
            data = board.get_current_board_data(sampling_size)
            action_dict[i].append(data)
    record_data["action_dict"] = action_dict

    # save record data
    print("Saving Data")
    
    # Iterate over any existant save files, deleting them if doOverwrite is True
    current_number = 0;
    while( True ):
        
        # Create the filenames that may exist in the directory, starting with record_eeg.pkl, then record_eeg1.pkl, etc.
        current_filename = create_filename( current_number )
            
        if( not os.path.isfile( current_filename ) ):
            break;
        
        if( doOverwrite ):
            os.remove( current_filename )
        current_number += 1
    
    filename_target = SAVE_FILENAME + SAVE_EXTENSION if doOverwrite else current_filename
    with open( filename_target, 'wb' ) as f:
        pickle.dump( record_data, f )
    
    board.stop_stream()
    board.release_session()

def create_filename( number ):
    filename = SAVE_FILENAME
    if( number != 0 ):
        filename += str( number )
    return filename + SAVE_EXTENSION

if __name__ == "__main__":
    main()