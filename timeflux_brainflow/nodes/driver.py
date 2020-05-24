import time
import pandas as pd
from brainflow.board_shim import (
    BoardIds,
    BoardShim,
    BrainFlowInputParams,
    BrainFlowError,
)
from timeflux.core.node import Node


class BrainFlow(Node):

    """Driver for BrainFlow.

    This plugin provides a unified interface for all boards supported by BrainFlow.

    Attributes:
        o (Port): Default output, provides DataFrame.

    Args:
        board (string|int): The board ID.
            Allowed values: numeric ID or name (e.g. ``synthetic``, ``cyton_wifi``,
            ``brainbit``).
        channels (list): The EEG channel labels.
            If not set, incrementing numbers will be used.
        debug (boolean): Print debug messages.
        **kwargs: The parameters specific for each board.
            Allowed arguments: ``serial_port``, ``mac_address``, ``ip_address``,
            ``ip_port``, ``ip_protocol``, ``serial_number``, ``other_info``.

    .. seealso::
        List of `supported boads <https://brainflow.readthedocs.io/en/stable/SupportedBoards.html>`_.

    Example:
        .. literalinclude:: /../examples/synthetic.yaml
           :language: yaml
    """

    def __init__(self, board, channels=None, debug=False, **kwargs):

        # Get board id
        if isinstance(board, str):
            # Board name
            try:
                self._board_id = getattr(BoardIds, board.upper() + "_BOARD").value
            except AttributeError:
                raise ValueError(f"Invalid board name: `{board}`") from None
        else:
            # Assume this is a numeric ID
            try:
                BoardIds(board)  # Attempt to access by value
                self._board_id = board
            except ValueError:
                raise ValueError(f"Invalid board ID: `{board}`") from None

        # Enable or disable debug mode
        if debug:
            BoardShim.enable_dev_board_logger()
        else:
            BoardShim.disable_board_logger()

        # Set board parameters
        params = BrainFlowInputParams()
        for key, value in kwargs.items():
            setattr(params, key, str(value))

        # Set private variables
        self._channels = list(range(0, BoardShim.get_num_rows(self._board_id)))
        self._timestamp_channel = BoardShim.get_timestamp_channel(self._board_id)
        self._counter_channel = BoardShim.get_package_num_channel(self._board_id)
        self._meta = {"rate": BoardShim.get_sampling_rate(self._board_id)}

        # Set channel labels
        accel_channels = self._rename_channels("accel", ("x", "y", "z"))
        gyro_channels = self._rename_channels("gyro", ("x", "y", "z"))
        analog_channels = self._rename_channels("analog")
        other_channels = self._rename_channels("other")
        eeg_channels = BoardShim.get_eeg_channels(self._board_id)
        num_eeg_channels = len(eeg_channels)
        if channels is not None:
            if not isinstance(channels, list) or len(channels) != num_eeg_channels:
                self.logger.warn(f"`channels` must contain {num_eeg_channels} elements")
                channels = None
        if channels is None:
            channels = [f"eeg_{channel}" for channel in range(1, num_eeg_channels + 1)]
        for channel, label in zip(eeg_channels, channels):
            self._channels[channel] = label
        self._channels[self._counter_channel] = "counter"
        self._channels[self._timestamp_channel] = "timestamp"

        # Initialize board and start streaming
        self._board = BoardShim(self._board_id, params)
        self._board.prepare_session()
        self._board.start_stream()

    def update(self):
        data = self._board.get_board_data()
        if data is not None:
            # TODO: check self._counter_channel and warn if we missed a packet
            indices = pd.to_datetime(data[self._timestamp_channel], unit="s")
            self.o.set(data.T, indices, self._channels, self._meta)

    def terminate(self):
        self._board.stop_stream()
        self._board.release_session()

    def _rename_channels(self, type, indices=None):
        try:
            channels = getattr(BoardShim, f"get_{type}_channels")(self._board_id)
        except BrainFlowError:
            return
        if indices:
            items = zip(indices, channels)
        else:
            items = enumerate(channels, start=1)
        for index, channel in items:
            self._channels[channel] = f"{type}_{index}"
