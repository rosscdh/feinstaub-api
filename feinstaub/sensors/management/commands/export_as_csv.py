# coding=utf-8
import os
import datetime
from itertools import product

from django.core.management import BaseCommand


def str2date(str, default):
    return datetime.datetime.strptime(str, '%Y-%m-%d').date() if str else default


class Command(BaseCommand):

    help = "Dump all Sensordata to csv files"

    def add_arguments(self, parser):
        parser.add_argument('--start_date')
        parser.add_argument('--end_date')

    def handle(self, *args, **options):
        from sensors.models import Sensor, SensorData

        # default yesterday
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        start_date = str2date(options.get('start_date'), yesterday)
        end_date = str2date(options.get('end_date'), yesterday)

        if start_date > end_date:
            print("end_date is before start_date")
            return

        folder = "/opt/code/archive"

        for dt, sensor in product(self._dates(start_date, end_date), Sensor.objects.all()):
            # first only for ppd42ns.
            # because we need a list of fields for all other sensors
            # -> SENSOR_TYPE_CHOICES needs to become more sophisticated
            if not sensor.sensor_type.name.lower() == "ppd42ns":
                continue

            # location 11 is the dummy location. remove the datasets.
            # remove all indoor locations
            qs = SensorData.objects \
                .filter(sensor=sensor) \
                .exclude(location_id=11) \
                .exclude(location__indoor=True) \
                .filter(timestamp__date=dt) \
                .order_by("timestamp")
            if not qs.exists():
                continue

            fn = '{date}_{stype}_sensor_{sid}.csv'.format(
                date=str(dt),
                stype=sensor.sensor_type.name.lower(),
                sid=sensor.id,
            )
            print(fn)
            os.makedirs(os.path.join(folder, str(dt)), exist_ok=True)

            # if file exists; overwrite. always
            with open(os.path.join(folder, str(dt), fn), "w") as fp:
                fp.write("sensor_id;sensor_type;location;lat;lon;timestamp;")
                # FIXME: generate from SENSOR_TYPE_CHOICES
                fp.write("P1;durP1;ratioP1;P2;durP2;ratioP2\n")
                for sd in qs:
                    sensordata = {
                        data['value_type']: data['value']
                        for data in sd.sensordatavalues.values('value_type', 'value')
                    }
                    if not sensordata:
                        continue
                    if 'P1' not in sensordata:
                        continue

                    longitude = ''
                    if sd.location.longitude:
                        longitude = "{:.3f}".format(sd.location.longitude)
                    latitude = ''
                    if sd.location.latitude:
                        latitude = "{:.3f}".format(sd.location.latitude)
                    s = ';'.join([str(sensor.id),
                                  sensor.sensor_type.name,
                                  str(sd.location.id),
                                  latitude,
                                  longitude,
                                  sd.timestamp.isoformat()])

                    fp.write(s)
                    fp.write(';')
                    fp.write('{};'.format(sensordata['P1']))
                    fp.write('{};'.format(sensordata['durP1']))
                    fp.write('{};'.format(sensordata['ratioP1']))
                    fp.write('{};'.format(sensordata['P2']))
                    fp.write('{};'.format(sensordata['durP2']))
                    fp.write('{}'.format(sensordata['ratioP2']))
                    fp.write("\n")

    @staticmethod
    def _dates(start, end):
        current = start
        while current <= end:
            yield current
            current += datetime.timedelta(days=1)
