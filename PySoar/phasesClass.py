from generalFunctions import det_local_time, determine_distance, det_bearing, det_bearing_change, ss2hhmmss, det_height


class FlightPhases(object):
    def __init__(self, competition_day):
        self.all = []
        self.leg = {}

        for leg in range(competition_day.no_legs):
            self.leg[str(leg+1)] = []

    def create_entry(self, i_start, t_start, phase, all_leg):
        content = {'i_start': i_start, 'i_end': i_start, 't_start': t_start, 't_end': t_start, 'phase': phase}
        if all_leg == 'all':
            self.all.append(content)
        if all_leg.startswith('leg'):
            self.leg[all_leg[-1]].append(content)

    def close_entry(self, i_end, t_end, all_leg):
        if all_leg == 'all':
            self.all[-1]['i_end'] = i_end
            self.all[-1]['t_end'] = t_end
        if all_leg.startswith('leg'):
            self.leg[all_leg[-1]][-1]['i_end'] = i_end
            self.leg[all_leg[-1]][-1]['t_end'] = t_end

    def determine_phases(self, settings, competitionday, flight):

        b_record_m1 = flight.b_records[flight.tsk_i[0] - 2]
        time_m1 = det_local_time(b_record_m1, competitionday.utc_to_local)

        b_record = flight.b_records[flight.tsk_i[0] - 1]
        time = det_local_time(b_record, competitionday.utc_to_local)
        bearing = det_bearing(b_record_m1, b_record, 'pnt', 'pnt')

        cruise = True
        possible_cruise_start = 0
        possible_thermal_start = 0
        cruise_distance = 0
        temp_bearing_change = 0
        possible_turn_dir = 'left'
        start_circle = 0
        bearing_change_tot = 0
        leg = 1

        self.create_entry(flight.tsk_i[0], time_m1, 'cruise', 'all')
        self.create_entry(flight.tsk_i[0], time_m1, 'cruise', 'leg'+str(leg))

        for i in range(flight.b_records.__len__()):
            if flight.tsk_i[0] < i < flight.tsk_i[-1]:

                time_m2 = time_m1

                time_m1 = time
                bearing_m1 = bearing
                b_record_m1 = b_record

                b_record = flight.b_records[i]
                time = det_local_time(b_record, competitionday.utc_to_local)

                bearing = det_bearing(b_record_m1, b_record, 'pnt', 'pnt')

                bearing_change_rate = det_bearing_change(bearing_m1, bearing) / (time - 0.5*time_m1 - 0.5*time_m2)

                if i == flight.tsk_i[leg]:
                    phase = 'cruise' if cruise else 'thermal'
                    leg += 1
                    self.close_entry(i, time, 'leg'+str(leg-1))
                    self.create_entry(i, time, phase, 'leg'+str(leg))

                if cruise:

                    if (possible_turn_dir == 'left' and bearing_change_rate < 1e-2) or\
                            (possible_turn_dir == 'right' and bearing_change_rate > -1e-2):

                        bearing_change_tot += det_bearing_change(bearing_m1, bearing)

                        if possible_thermal_start == 0:
                            possible_thermal_start = i
                        elif start_circle == 0 and abs(bearing_change_rate) > settings.glide_threshold_bearingRate:
                            start_circle = i
                            possible_thermal_start = i

                    else:  # sign change
                        bearing_change_tot = det_bearing_change(bearing_m1, bearing)

                        if bearing_change_rate < 0:
                            possible_turn_dir = 'left'
                        else:
                            possible_turn_dir = 'right'

                        possible_thermal_start = i

                    if abs(bearing_change_tot) > settings.turn_threshold_bearingTot:
                        cruise = False
                        self.close_entry(i, time, 'all')
                        self.close_entry(i, time, 'leg' + str(leg))
                        self.create_entry(start_circle, time, 'thermal', 'all')
                        self.create_entry(start_circle, time, 'thermal', 'leg'+str(leg))
                        possible_thermal_start = 0
                        start_circle = 0
                        bearing_change_tot = 0

                else:  # thermal
                    if abs(bearing_change_rate) > settings.turn_threshold_bearingRate:
                        if possible_cruise_start != 0:
                            cruise_distance = 0
                            temp_bearing_change = 0
                    else:  # possible cruise
                        if cruise_distance == 0:
                            possible_cruise_start = i
                            possible_cruise_t = time
                            temp_bearing_change += bearing_change_rate
                            temp_bearing_avg = 0
                        else:
                            temp_bearing_change += bearing_change_rate
                            temp_bearing_avg = temp_bearing_change / (time-possible_cruise_t)

                        cruise_distance = determine_distance(flight.b_records[possible_cruise_start-1], b_record,
                                                             'pnt', 'pnt')

                        if cruise_distance > settings.glide_threshold_dist and \
                                        abs(temp_bearing_avg) < settings.glide_threshold_bearingRateAvg:

                            cruise = True
                            self.close_entry(i, time, 'all')
                            self.close_entry(i, time, 'leg'+str(leg))
                            self.create_entry(possible_cruise_start, possible_cruise_t, 'cruise', 'all')
                            self.create_entry(possible_cruise_start, possible_cruise_t, 'cruise', 'leg'+str(leg))
                            possible_cruise_start = 0
                            cruise_distance = 0
                            temp_bearing_change = 0

        time = det_local_time(flight.b_records[flight.tsk_i[-1]], competitionday.utc_to_local)
        self.close_entry(flight.tsk_i[-1], time, 'all')
        self.close_entry(flight.tsk_i[-1], time, 'leg'+str(leg))


    def append_differences(self, difference_indicators, leg):
        for key, value in difference_indicators:
            self.pointwise_all[key].append(value)
            self.pointwise_leg[leg][key].append(value)

    def get_difference_indicators(self):
        return ['height_difference', 'distance', 'time_difference', 'phase']

    def determine_point_statistics(self, flight, competition_day):
        self.pointwise_all = {}
        self.pointwise_leg = []

        for leg in range(competition_day.no_legs):
            for indicator in self.get_difference_indicators():
                self.pointwise_leg.append({indicator: []})

        phase_number = 0
        leg = 1
        phase = self.all[phase_number]['phase']
        phase_number += 1

        for i in range(flight.b_records.__len__()):
            if flight.tsk_i[0] <= i < flight.tsk_i[-1]:

                if self.all[phase_number]['i_start'] == i:
                    phase = self.all[phase_number]['phase']
                    phase_number += 1

                if i == flight.tsk_i[leg]:
                    leg += 1

                height_difference = det_height(flight.b_records[i+1], flight.gps_altitude) -\
                                    det_height(flight.b_records[i], flight.gps_altitude)
                distance = determine_distance(flight.b_records[i], flight.b_records[i+1], 'pnt', 'pnt')
                time_difference = det_local_time(flight.b_records[i+1], competition_day.utc_to_local) -\
                                  det_local_time(flight.b_records[i], competition_day.utc_to_local)

                difference_indicators = {'height_difference': height_difference,
                                         'distance': distance,
                                         'time_difference': time_difference,
                                         'phase': phase}

                self.append_differences(difference_indicators, leg)

    def print_phases(self):
        for entry in self.all:
            print 'phase:', entry['phase'], 't_start=', ss2hhmmss(entry['t_start']), ' t_end=', ss2hhmmss(entry['t_end']), 'i=', entry['i_start'], ' till i=', entry['i_end']
        for key in self.leg.iterkeys():
            for entry in self.leg[key]:
                print 'leg', key, 'phase:', entry['phase'], 't_start=', ss2hhmmss(entry['t_start']),\
                    ' t_end=', ss2hhmmss(entry['t_end']), 'i=', entry['i_start'], ' till i=', entry['i_end']
        print self.pointwise_all
        print self.pointwise_leg

if __name__ == '__main__':
    from main import run

    run()