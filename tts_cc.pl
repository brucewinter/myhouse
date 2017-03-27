#!/usr/bin/perl

# Stand alone mqtt test examples:
#   mosquitto_pub -t "chromecast/office/command" -m "set_volume|100"
#   mosquitto_pub -t "chromecast/office/command" -m "set_volume|100"

use strict;
use Net::MQTT::Simple;
use URI::Escape;

$| = 1;

my $server = '192.168.86.150';
my $cache_dir = '/home/bruce/mh/local/data/cache';
my %room_defaults = (bedroom => 60, downstairs => 80,  guestroom => 70, kitchen => 60, office => 60,  deck => 80, treehouse => 80);

my (%parms, $text, $file, $mqtt_server);
use Getopt::Long;
if (!&GetOptions(\%parms, 'h', 'd', 'help', 'room=s', 'voice=s', 'volume=s', 'card=s') or !@ARGV or $parms{h} or $parms{help}) {
 print<<eof;
 
 Calls a cloud based TTS (Text To Speech) engine, then caches and plays the resulting sound file over chromecast devices

    -h        => This help text
    -d        => Add debug

    -room   => a,b,c Speak to just room a,b,c
    -voice  => xyz   Use voice xyz
    -volume => ddd   Set volume to ddd (default is 100)
    -card   => xyz   Use card xyz
														      

eof
    exit;
}

&setup;
&tts_to_file;
&play_file;

sub setup {
    $text = "@ARGV";
    $file = lc(substr $text, 0, 100);
    $file =~ s/ +/ /g;
    $file =~ s/\W/_/g;
    $file = "$cache_dir/$file";
    $parms{volume} = 100 unless $parms{volume};
#   $parms{room} = ''  if $parms{room} eq 'all';
    $parms{card} = '1' if $parms{room} eq 'bruce';
    $parms{room} = ''  if $parms{room} eq 'bruce';
    print "db tts: t=$text room=$parms{room} voice=$parms{voice} volume=$parms{volume} card=$parms{card} f=$file.\n" if $parms{d};

    $mqtt_server = Net::MQTT::Simple->new($server);
    $mqtt_server->publish("mh/speak_start" => $text);  # Used to detect when house is speaking, so we can stage speech, like in speak_insult.pl
}


# IBM Watson, limited to 3 calls a minute.
#  - https://github.com/watson-developer-cloud/text-to-speech-nodejs
#  - https://text-to-speech-nodejs-brucewinter-1234.mybluemix.net/
#  - http://www.ibm.com/smarterplanet/us/en/ibmwatson/developercloud/text-to-speech.html
#  - The supported voice are Michael(Male), Lisa(Female), Allison(Female) and Kate(Female ... does not work?).    
# Other TTS engines.   
#   Google:     Now requires capth.   http://translate.google.com/translate_tts?tl=en&client=mh&q=$text
#   VoiceRSS:   More mechanical.      http://api.voicerss.org/?key=9d167964640e4e7eaafc190f467b44d0&&hl=en-ca&src=$text
#   Vocalware:  $3 per 1000 calls:   https://www.vocalware.com/support/faq

sub tts_to_file {    
    if (!-e $file or $parms{voice}) {
#	$text =~ s/ /\%20/g;
#	$text =~ s/\"/\%22/g;
#	$text =~ s/\'/\%27/g;
	$text =~ s/[<>]/ /g;  # This can look like illegal xml tags
	$text = uri_escape($text);
	$parms{voice} = "Michael" unless $parms{voice};
	my $url = "https://watson-api-explorer.mybluemix.net/text-to-speech/api/v1/synthesize?accept=audio%2Fwav";
	$url .= "&voice=en-US_$parms{voice}Voice&text=$text";
	my $curl = "curl -X GET --header 'Accept: audio/wav' '$url' > $file";
	$curl .= qq| > /dev/null  2>&1| unless $parms{d};
	print "to_file cmd: $curl\n" if $parms{d};
	system $curl;

	my $size = -s $file;   # 'hi' file is 37k, so anything smaller is bad
	if ($size < 20000) {
	    print "tts: audio file is too small: s=$size f=$file\n";
	    unlink $file;
	    $file = "$cache_dir/speak_error";
	}
    }
}

sub play_file {
    open (IN, '<', $file); binmode(IN); $/ = undef; my $data =  <IN>; 

    my $file_lock = "$cache_dir/tts.lock";   # Play only 1 file at a time
    while (-e $file_lock) { sleep 1; last if 10 < time - (stat($file_lock))[9]}
    `touch $file_lock`;
    
    &set_rooms($parms{room});

#   my $cmd = 'play '; 
#   my $cmd = 'mplayer ';   # mplayer supports -volume
#   $cmd .= "-volume $parms{volume} " if $parms{volume};
    my $cmd = 'paplay ';    # mplayer supports -volume
    $cmd .= " --volume=" . 65535*$parms{volume}/100 if $parms{volume};
    $cmd .= " --device=" . $parms{card} if $parms{card};

    $cmd .= " $file";
    $cmd .= " > /dev/null 2>&1" unless $parms{d};
    print "db tts: c=$cmd\n" if $parms{d};
    system $cmd;
    
#    sleep 4;
#    &reset_room_volumes($parms{room});

    $mqtt_server->publish("mh/speak_done" => $text);  
    unlink $file_lock;
    print "all done\n" if $parms{d};
}


sub set_rooms {
    my ($rooms) = @_;
    my %rooms = map { $_ => 1 } split ',', $rooms;
    if (%rooms) {
	for my $room (keys %room_defaults) {
	    my $m = ($rooms{$room} | $rooms eq 'all') ? 'unmute' : 'mute';
	    print "db tts: r=$room r2=$rooms{$room} m=$m\n" if $parms{d};
	    $mqtt_server->publish("chromecast/$room/command" => "set_volume_$m");
	}
    }
}

sub reset_room_volumes {
    my ($rooms) = @_;
    print "db reset room volues\n";
    if ($rooms) {
	for my $room (keys %room_defaults) {
	    my $v =  $room_defaults{$room};
	    print "db tts: r=$room v=$v\n" if $parms{d};
#	    $mqtt_server->publish("chromecast/$room/command" => "set_volume|$v") if $rooms{$room};
	}
    }
}


__END__
