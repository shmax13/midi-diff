import matplotlib.colors
import mido
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# color constants
BLACK = 1
RED = 2
GREEN = 3


class MidiFile(mido.MidiFile):

    def __init__(self, filename):

        mido.MidiFile.__init__(self, filename)
        self.meta = {}
        self.events = self.get_events()
        self.note_list = self.get_note_list()
        self.old = True

    # iterate over all events in the MIDI file and extract it to 'events' array
    def get_events(self):

        events = [[] for _ in range(16)]

        for track in self.tracks:
            for msg in track:
                try:
                    # parse note events
                    channel = msg.channel
                    events[channel].append(msg)
                except AttributeError:
                    # parse metadata
                    if type(msg) != type(mido.UnknownMetaMessage):
                        self.meta[msg.type] = msg.dict()
                    else:
                        pass
        return events

    # create a note list from the list of events. color all notes black
    def get_note_list(self):

        events = self.events

        # use a register array to save the state(on/off) for each key
        note_register = [int(-1) for _ in range(128)]

        # list with notes
        note_list = []

        for idx, channel in enumerate(events):

            time_counter = 0

            for msg in channel:

                if msg.type == "note_on":

                    # when a note_on event *ends* the note starts to be played!
                    note_on_end_time = (time_counter + msg.time)

                    if note_register[msg.note] == -1:
                        # note starts. store start time in register
                        note_register[msg.note] = note_on_end_time
                    else:
                        # note starts over. store new start time in register and add ending note to note list
                        note_start_time = note_register[msg.note]
                        note_list.append((idx, msg.note, note_start_time, note_on_end_time, BLACK))
                        note_register[msg.note] = note_on_end_time

                if msg.type == "note_off":
                    note_off_end_time = (time_counter + msg.time)

                    # note ends. reset it in register and add it to the note list
                    note_start_time = note_register[msg.note]
                    note_list.append((idx, msg.note, note_start_time, note_off_end_time, BLACK))
                    note_register[msg.note] = -1

                time_counter += msg.time

            # if there is a note not closed at the end of the sequence, close it
            for key, data in enumerate(note_register):
                if data != -1:
                    note_start_time = data
                    note_list.append((idx, key, note_start_time, time_counter, BLACK))
                note_register[idx] = -1
        return note_list

    # compare the older version of a file to the newer one. color changed notes red or green
    def compare_to_new(self, new):
        old_note_list = self.note_list
        new_note_list = new.note_list
        result_note_list = []

        for entry in old_note_list:
            if entry[0] == channel_id and entry in new_note_list:
                # note exists in new version, color it black
                result_note_list.append((entry[0], entry[1], entry[2], entry[3], BLACK))
            else:
                # note does not exist anymore in new version, color it red
                result_note_list.append((entry[0], entry[1], entry[2], entry[3], RED))

        self.note_list = result_note_list

    # compare the newer version of a file to the older one
    def compare_to_old(self, old):
        old_note_list = old.note_list
        new_note_list = self.note_list
        result_note_list = []

        for entry in new_note_list:
            if entry[0] == channel_id and entry in old_note_list:
                # note exists in previous version, color it black
                result_note_list.append((entry[0], entry[1], entry[2], entry[3], BLACK))
            else:
                # note does not exist yet in previous version, color it green
                result_note_list.append((entry[0], entry[1], entry[2], entry[3], GREEN))

        self.note_list = result_note_list

    def get_tempo(self):
        return self.meta["set_tempo"]["tempo"]

    def get_total_ticks(self):
        max_ticks = 0
        for channel in range(16):
            ticks = sum(msg.time for msg in self.events[channel])
            if ticks > max_ticks:
                max_ticks = ticks
        return max_ticks

    # reload note list of the selected channel
    def reload(self):
        self.note_list = self.get_note_list()


# draws the roll consisting of plots of both MIDI files
def draw_roll():

    length_old = midi_old.get_total_ticks()
    length_new = midi_new.get_total_ticks()

    # 16 channels, 128 midi notes, length of file
    piano_roll_old = np.zeros((16, 128, length_old), dtype="int8")
    piano_roll_new = np.zeros((16, 128, length_new), dtype="int8")

    # fill rolls with note list entries
    for entry in midi_old.note_list:
        piano_roll_old[entry[0], entry[1], entry[2]:entry[3]] = entry[4]
    for entry in midi_new.note_list:
        piano_roll_new[entry[0], entry[1], entry[2]:entry[3]] = entry[4]

    # build plot and subplots
    plt.ioff()
    fig = plt.figure(figsize=(15, 12))
    fig.tight_layout()
    fig.suptitle('Showing MIDI diff in channel ' + str(channel_id), size="25")

    plot_old = fig.add_subplot(2, 1, 1)
    plot_old.axis("equal")
    plot_old.set_facecolor("white")
    plot_old.set_xlabel("time (s)")
    plot_old.set_ylabel("note (midi number)")

    plot_new = fig.add_subplot(2, 1, 2)
    plot_new.axis("equal")
    plot_new.set_facecolor("white")
    plot_new.set_xlabel("time (s)")
    plot_new.set_ylabel("note (midi number)")

    # change unit of time axis from ticks to second for both plots
    tick_old = midi_old.get_total_ticks()
    tick_new = midi_new.get_total_ticks()
    second_old = mido.tick2second(tick_old, midi_old.ticks_per_beat, midi_old.get_tempo())
    second_new = mido.tick2second(tick_new, midi_new.ticks_per_beat, midi_new.get_tempo())
    if second_old > 10:
        x_label_period_sec_old = second_old // 10
    else:
        x_label_period_sec_old = second_old / 10
    if second_new > 10:
        x_label_period_sec_new = second_new // 10
    else:
        x_label_period_sec_new = second_new / 10
    x_label_interval_old = mido.second2tick(x_label_period_sec_old, midi_old.ticks_per_beat, midi_old.get_tempo())
    x_label_interval_new = mido.second2tick(x_label_period_sec_new, midi_new.ticks_per_beat, midi_new.get_tempo())

    # change scale and label of x-axis for both plots
    plot_old.set_xticks([int(x * x_label_interval_old) for x in range(20)])
    plot_old.set_xticklabels([round(x * x_label_period_sec_old, 2) for x in range(20)])
    plot_new.set_xticks([int(x * x_label_interval_new) for x in range(20)])
    plot_new.set_xticklabels([round(x * x_label_period_sec_new, 2) for x in range(20)])
    # change scale and label of y-axis for both plots
    plot_old.set_yticks([y * 16 for y in range(8)])
    plot_old.set_yticklabels([y * 16 for y in range(8)])
    plot_new.set_yticks([y * 16 for y in range(8)])
    plot_new.set_yticklabels([y * 16 for y in range(8)])

    # customize plot colors
    colors = [(1, 1, 1), (0, 0, 0), (1, 0, 0), (0, 1, 0)]  # white, black, red, green
    cmap_name = 'my_colors'
    cmap = mpl.colors.LinearSegmentedColormap.from_list(cmap_name, colors)
    bounds = np.linspace(0, 4, 5)
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

    # show plot with subplots
    plot_old.imshow(piano_roll_old[channel_id], origin="lower", interpolation='nearest',
                    cmap=cmap, norm=norm, aspect='auto')
    plot_new.imshow(piano_roll_new[channel_id], origin="lower", interpolation='nearest',
                    cmap=cmap, norm=norm, aspect='auto')

    # show piano roll
    plot_old.title.set_text('File: ' + midi_old.filename)
    plot_new.title.set_text('File: ' + midi_new.filename)
    plt.draw()
    plt.ion()
    plt.show(block=True)


if __name__ == "__main__":
    # step 1: parse MIDI files
    midi_old = MidiFile("test_file/fl_air.mid")
    midi_old.old = True
    midi_new = MidiFile("test_file/fl_dancing_queen.mid")
    midi_new.old = False

    if midi_old.get_total_ticks() != midi_new.get_total_ticks():
        print('WARNING: Please choose two MIDI files of the same length!')

    try:
        while True:
            # step 2: reload MIDI files
            midi_old.reload()
            midi_new.reload()

            # step 3: take user input on which channel should be compared
            channel_id = int(input('Which MIDI channel do you want to compare? (0 <= i <= 15)\n'))

            # step 4: compare MIDI files and create an array with note objects (pitch, start, end, color)
            midi_old.compare_to_new(midi_new)
            midi_new.compare_to_old(midi_old)

            # step 5: draw MIDI diff view
            draw_roll()
    except ValueError or IndexError:
        pass
    except KeyboardInterrupt:
        print("Exiting.")
        pass
