import matplotlib.colors
import mido
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

BLACK = 1
RED = 2
GREEN = 3


class MidiFile(mido.MidiFile):

    def __init__(self, filename):

        mido.MidiFile.__init__(self, filename)
        self.sr = 10
        self.meta = {}
        self.events = self.get_events()
        self.note_list = self.get_note_list()
        self.old = True

    def get_events(self):
        mid = self
        # print(mid)

        # There is > 16 channel in midi.tracks. However, there is only 16 channel related to "music" events.
        # We store music events of 16 channel in the list "events" with form [[ch1],[ch2]....[ch16]]
        # Lyrics and metadata used an extra channel which is not include in "events"

        events = [[] for x in range(16)]

        # Iterate all event in the midi and extract to 16 channel form
        for track in mid.tracks:
            for msg in track:
                try:
                    channel = msg.channel
                    events[channel].append(msg)
                except AttributeError:
                    try:
                        if type(msg) != type(mido.UnknownMetaMessage):
                            self.meta[msg.type] = msg.dict()
                        else:
                            pass
                    except:
                        print("error", type(msg))

        return events

    def get_note_list(self):

        events = self.events
        sr = self.sr

        # use a register array to save the state(on/off) for each key
        note_register = [int(-1) for i in range(128)]

        # list with notes
        note_list = []

        for idx, channel in enumerate(events):

            time_counter = 0
            volume = 100
            # Volume would change by control change event (cc) cc7 & cc11
            # Volume 0-100 is mapped to 0-127

            # print("channel", idx, "start")
            for msg in channel:

                if msg.type == "note_on":
                    # print("on ", msg.note, "time", time_counter, "duration", msg.time, "velocity", msg.velocity)
                    note_on_start_time = time_counter // sr
                    note_on_end_time = (time_counter + msg.time) // sr

                    # When a note_on event *ends* the note start to be play
                    # Record end time of note_on event if there is no value in register
                    # When note_off event happens, we fill in the color
                    if note_register[msg.note] == -1:
                        note_register[msg.note] = note_on_end_time
                    else:
                        # When note_on event happens again, we also fill in the color
                        note_start_time = note_register[msg.note]
                        note_list.append((idx, msg.note, note_start_time, note_on_end_time, 1))
                        note_register[msg.note] = note_on_end_time

                if msg.type == "note_off":
                    # print("off", msg.note, "time", time_counter, "duration", msg.time, "velocity", msg.velocity)
                    note_off_start_time = time_counter // sr
                    note_off_end_time = (time_counter + msg.time) // sr

                    note_start_time = note_register[msg.note]
                    note_list.append((idx, msg.note, note_start_time, note_off_end_time, 1))
                    note_register[msg.note] = -1

                time_counter += msg.time

            # if there is a note not closed at the end of a channel, close it
            for key, data in enumerate(note_register):
                if data != -1:
                    note_start_time = data
                    note_list.append((idx, key, note_start_time, 10000000, 1))
                note_register[idx] = -1
        return note_list

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

    def reload(self):
        self.note_list = self.get_note_list()


def draw_roll():
    # build and set fig obj

    sr_old = midi_old.sr
    sr_new = midi_new.sr
    length_old = midi_old.get_total_ticks()
    length_new = midi_new.get_total_ticks()

    piano_roll_old = np.zeros((16, 128, length_old // sr_old), dtype="int8")
    piano_roll_new = np.zeros((16, 128, length_new // sr_new), dtype="int8")

    for entry in midi_old.note_list:
        piano_roll_old[entry[0], entry[1], entry[2]:entry[3]] = entry[4]
    for entry in midi_new.note_list:
        piano_roll_new[entry[0], entry[1], entry[2]:entry[3]] = entry[4]

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

    # change unit of time axis from tick to second
    tick = midi_new.get_total_ticks()
    second = mido.tick2second(tick, midi_new.ticks_per_beat, midi_new.get_tempo())
    # print(second)
    if second > 10:
        x_label_period_sec = second // 10
    else:
        x_label_period_sec = second / 10  # ms
    # print(x_label_period_sec)
    x_label_interval = mido.second2tick(x_label_period_sec, midi_new.ticks_per_beat, midi_new.get_tempo()) / midi_new.sr
    # print(x_label_interval)

    # change scale and label of x-axis
    plot_old.set_xticks([int(x * x_label_interval) for x in range(20)])
    plot_old.set_xticklabels([round(x * x_label_period_sec, 2) for x in range(20)])
    plot_new.set_xticks([int(x * x_label_interval) for x in range(20)])
    plot_new.set_xticklabels([round(x * x_label_period_sec, 2) for x in range(20)])
    # change scale and label of y-axis
    plot_old.set_yticks([y * 16 for y in range(8)])
    plot_old.set_yticklabels([y * 16 for y in range(8)])
    plot_new.set_yticks([y * 16 for y in range(8)])
    plot_new.set_yticklabels([y * 16 for y in range(8)])

    colors = [(1, 1, 1), (0, 0, 0), (1, 0, 0), (0, 1, 0)]
    cmap_name = 'my_colors'
    cmap = mpl.colors.LinearSegmentedColormap.from_list(cmap_name, colors)
    bounds = np.linspace(0, 4, 5)
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

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
    midi_old = MidiFile("test_file/fl_dancing_queen.mid")
    midi_old.old = True
    midi_new = MidiFile("test_file/fl_air.mid")
    midi_new.old = False

    if midi_old.get_total_ticks() != midi_new.get_total_ticks():
        print('WARNING: Please choose two MIDI files of the same length!')

    try:
        while True:
            midi_old.reload()
            midi_new.reload()

            channel_id = int(input('Which MIDI channel do you want to compare? (0 <= i <= 15)\n'))

            # step 2: compare MIDI files, and create an array with colors (pitch, start, end, color)
            midi_old.compare_to_new(midi_new)
            midi_new.compare_to_old(midi_old)

            # step 3: draw MIDI piano rolls
            draw_roll()
    except ValueError or IndexError:
        pass
    except KeyboardInterrupt:
        print("Exiting.")
        pass
