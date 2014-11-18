

=begin comment

This object supports reading/writing to the micasaverde.com vera interface.

Useful docs:   http://wiki.micasaverde.com/index.php/Luup_UPnP_Variables_and_Actions

Use this to list all possible data for all devices or one device
  http://192.168.0.120:3480/data_request?id=status&output_format=xml
  http://192.168.0.120:3480/data_request?id=status&output_format=xml&DeviceNum=92

To track vera sensors, use luup code in each device, like this:  luup.inet.wget("http://192.168.0.150:8080/SET;none?$motion_front_door=on")

Examples:

 Note:  Use the vera Device #, not the ID or altid (which is the z-wave node).
  
 $chandelier_light  = new Vera_Item 'light',   1;
 $tstat_up          = new Vera_Item 'tstat',   2;
 $motion_front_door = new Vera_Item 'motion',  3;
 $curtain_1         = new Vera_Item 'curtain', 4;
 $front_door_lock   = new Vera_Item 'lock',    5;

=cut

use strict;

package Vera_Item;

@Vera_Item::ISA = ('Generic_Item');

sub new {
    my ($class, $type, $dnum) = @_;
    my %myhash;
    my $self = \%myhash;
    bless $self, $class;
    $self->{type} = $type;
    $self->{dnum} = $dnum;
    $self->{file} = "$::config_parms{data_dir}/Vera_Item.$dnum.status.txt";
    return $self;
}

sub set {
    my ($self, $state) = @_;
    $self->SUPER::set($state);
    return &set_vera($self, $state);
}

sub get_variable {
    my ($self, $var) = @_;

    my $type = $$self{type};
    my $dnum = $$self{dnum};
    my $vera_ip = $::config_parms{vera_ip_address};
    my $urn = 'micasaverde-com';
    my ($id, $sid);

    if ($var eq 'battery') {
	$id  = 'variableget';
	$sid = "HaDevice1&Variable=BatteryLevel";
    }
    elsif ($var eq 'battery_date') {
	$id = 'variableget';
	$sid = "HaDevice1&Variable=BatteryDate";
    }

    if ($sid) {
	my $url = "http://$vera_ip:3480/data_request?id=$id&output_format=text&DeviceNum=$dnum&serviceId=urn:$urn:serviceId:$sid";

# Avoid mh pauses by returning previous value.   If we need current data, request it twice.
#	my $data = main::get($url);

        my $data = &::file_read($$self{file});
	system "(curl -s '$url' > $$self{file}) &";

	print "vera name==$$self{object_name} data=$data ip=$vera_ip type=$type  dnum=$dnum var=$var sid=$sid u=$url\n" if $main::Debug{vera};
	return $data;
    }

}

sub set_vera {
    my ($self, $state) = @_;

    my $type = $$self{type};
    my $dnum = $$self{dnum};

    my $vera_ip = $::config_parms{vera_ip_address};

    my ($id, $urn, $sid, $state2);
    
    $id  = 'lu_action';
    $urn = 'upnp-org';

    if ($type eq 'light') {
	if ($state =~ /status/i) {
	    $id = 'variableget';
	    $sid = "SwitchPower1&Variable=Status";
	}
	elsif ($state =~ /toggle/i) {
	    $urn = 'micasaverde-com';
	    $sid = 'HaDevice1&action=ToggleState';
	}
	elsif ($state =~ /\d+/) {
	    $sid = "Dimming1&action=SetLoadLevelTarget&newLoadlevelTarget=$state";
	}
	else {
	    $state2 = '1' if $state =~ /on/i;
	    $state2 = '0' if $state =~ /off/i;
	    $sid = "SwitchPower1&action=SetTarget&newTargetValue=$state2";
	}

    }

    elsif ($type eq 'lock') {
	$urn = 'micasaverde-com';
	if ($state =~ /status/i) {
	    $id = 'variableget';
	    $sid = "DoorLock1&Variable=Status";
	}
	else {
	    $state2 = '1' if $state =~ /lock/i;
	    $state2 = '0' if $state =~ /unlock/i;
	    $sid = "DoorLock1&action=SetTarget&newTargetValue=$state2";
	}
    }

    elsif ($type eq 'tstat') {
	if ($state eq 'temperature') {
	    $id = 'variableget';
	    $sid = "TemperatureSensor1&Variable=CurrentTemperature";
	}
	elsif ($state eq 'setpoint') {
	    $id = 'variableget';
	    $sid = "TemperatureSetpoint1_Heat&Variable=CurrentSetpoint";
	}
	else {
	    if ($state =~ /^[\d\.]+$/) {
		$sid = "TemperatureSetpoint1_Heat&action=SetCurrentSetpoint&NewCurrentSetpoint=$state";
	    }
	    elsif ($state =~ /fan/) {
		$state2 = 'ContinuousOn' if $state =~ /on/i;
		$state2 = 'Auto'         if $state =~ /off/i;
		$sid = "HVAC_FanOperatingMode1&action=SetMode&NewMode=$state2";
	    }
	    elsif ($state =~ /hold/) {
		$state2 = '1' if $state =~ /on/i;
		$state2 = '0' if $state =~ /off/i;
		$sid = "HVAC_RTCOA_TemperatureHold1&action=SetTarget&newTargetValue=$state2";
		$urn = 'hugheaves-com';
	    }
	    else {
		$state2 = 'Off'            if $state =~ /off/i;
		$state2 = 'HeatOn'         if $state =~ /heat/i;
		$state2 = 'CoolOn'         if $state =~ /cool/i;
		$state2 = 'AutoChangeOver' if $state =~ /auto/i;
		$sid = "HVAC_UserOperatingMode1&action=SetModeTarget&NewModeTarget=$state2";
	    }

	}
    }

    elsif ($type eq 'curtain') {
#	$state2 = 'Up'   if lc $state eq 'up';
	$state2 = 'Down' if lc $state eq 'down';
	$state2 = 'Up'   if lc $state eq 'open';
	$state2 = 'Down' if lc $state eq 'close';
	$state2 = 'Stop' if lc $state eq 'stop';
	$state2 = 'Stop' if lc $state eq 'arrange';
	$sid = "WindowCovering1&action=$state2";
    }

    if ($sid) {
	my $url = "http://$vera_ip:3480/data_request?id=$id&output_format=text&DeviceNum=$dnum&serviceId=urn:$urn:serviceId:$sid";

# Avoid mh pauses by returning previous value.   If we need current data, request it twice.
#	my $data = main::get($url);

        my $data = &::file_read($$self{file});
	system "(curl -s '$url' > $$self{file}) &";

	print "vera name=$$self{object_name} data=$data ip=$vera_ip type=$type  dnum=$dnum state=$state sid=$sid u=$url\n" if $main::Debug{vera};
	return $data;
    }
}

1;

=begin comment

Examples

Doggy cam on
http://192.168.0.120:3480/data_request?id=lu_action&output_format=text&DeviceNum=89&serviceId=urn:upnp-org:serviceId:SwitchPower1&action=SetTarget&newTargetValue=1

Scene
scene xmas lights on: http://192.168.1.109:3480/data_request?id=lu_action&serviceId=urn:micasaverde-com:serviceId:HomeAutomationGateway1&action=RunScene&SceneNum=7   =8 for off


Lights
http://192.168.1.109:3480/data_request?id=lu_action&DeviceNum=35&serviceId=urn:micasaverde-com:serviceId:HaDevice1&action=ToggleState
http://192.168.1.109:3480/data_request?id=lu_action&DeviceNum=35&serviceId=urn:upnp-org:serviceId:SwitchPower1&action=SetTarget&newTargetValue=0   =1 for on
http://192.168.1.109:3480/data_request?id=lu_action&DeviceNum=40&serviceId=urn:upnp-org:serviceId:Dimming1&action=SetLoadLevelTarget&newLoadlevelTarget=20
http://192.168.1.109:3480/data_request?id=lu_action&DeviceNum=40&serviceId=urn:upnp-org:serviceId:Dimming1&action=SetLoadLevelTarget&newLoadlevelTarget=50

Tstat:
http://upnp.org/specs/ha/UPnP-ha-HVAC_ZoneThermostat-v1-Device.pdf
http://code.mios.com/trac/mios_wifi-thermostat/browser/tags/2.1/src/D_RTCOA_Wifi_ZoneThermostat1.json

http://192.168.1.120:3480/data_request?id=lu_action&output_format=xml&DeviceNum=24&serviceId=urn:upnp-org:serviceId:HVAC_FanOperatingMode1&action=SetMode&NewMode=ContinuousOn   Auto 
http://192.168.1.120:3480/data_request?id=variableget&DeviceNum=24&serviceId=urn:upnp-org:serviceId:HVAC_FanOperatingMode1&Variable=Mode
http://192.168.1.120:3480/data_request?id=lu_action&DeviceNum=25&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Heat&action=SetCurrentSetpoint&NewCurrentSetpoint=68
http://192.168.1.120:3480/data_request?id=lu_action&DeviceNum=25&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Cool&action=SetCurrentSetpoint&NewCurrentSetpoint=90
http://192.168.1.120:3480/data_request?id=variableget&DeviceNum=24&serviceId=urn:upnp-org:serviceId:TemperatureSensor1&Variable=CurrentTemperature
http://192.168.1.120:3480/data_request?id=lu_action&DeviceNum=25&serviceId=urn:upnp-org:serviceId:HVAC_RTCOA_TemperatureHold1&action=SetTarget&newTargetValue=0


Curtain:
http://192.168.1.109:3480/data_request?id=lu_action&output_format=xml&DeviceNum=8&serviceId=urn:upnp-org:serviceId:WindowCovering1&action=Stop  Up Down

status: 
 http://192.168.1.109:3480/data_request?id=sdata&output_format=text
 http://192.168.1.109:3480/data_request?id=sdata&output_format=text&DeviceNum=50   does not work ... gives all devices

Lock:
<state id="242" service="urn:micasaverde-com:serviceId:DoorLock1" variable="Status" value="0"/>
<state id="253" service="urn:micasaverde-com:serviceId:HaDevice1" variable="BatteryLevel" value="96"/>
 http://192.168.0.120:3480/data_request?id=variableget&output_format=text&DeviceNum=106&serviceId=urn:micasaverde-com:serviceId:DoorLock1&Variable=Status
 http://192.168.0.120:3480/data_request?id=variableget&output_format=text&DeviceNum=106&serviceId=urn:micasaverde-com:serviceId:HaDevice1&Variable=BatteryLevel


=cut 

