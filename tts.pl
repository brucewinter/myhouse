#!/usr/bin/perl
use strict;
use Net::MQTT::Simple;
use Time::HiRes qw( time sleep);
$| = 1;

my $text = "@ARGV";
my $room;
if ($text =~ /(.+)-room (\S+)/) {
    $text = $1;  $room = $2;
}

my $file = substr $text, 0, 100;
$file =~ s/\W/_/g;
$file = "/home/bruce/mh/local/data/cache/$file";

$text =~ s/ /\%20/g;

# can be .wav or .mp3??  Probably is a mp3, but mplayer will play no matter the extension
if (-e $file) {
}
else {

# 12/05/2015 Switch from google to voicerss, as google does capthas now. 
#   my $curl = "curl -s -A 'Mozilla' 'http://translate.google.com/translate_tts?tl=en&client=mh&q=$text' > $file";
#   my $curl = "curl -s -A 'Mozilla' 'http://api.voicerss.org/?key=your_key&&hl=en-ca&src=$text' > $file";

# Another option, $3 per 1000 calls: https://www.vocalware.com/support/faq

# Simple IBM watson option, limited to 3 calls a minute.  For more info an an IBM API:
#  https://github.com/watson-developer-cloud/text-to-speech-nodejs
#  http://www.ibm.com/smarterplanet/us/en/ibmwatson/developercloud/text-to-speech.html
    my $curl = "curl -X GET --header 'Accept: audio/wav' 'https://watson-api-explorer.mybluemix.net/text-to-speech/api/v1/synthesize?accept=audio%2Fwav&voice=en-US_MichaelVoice&text=$text' > $file";
#   $curl .= qq| > /dev/null |;

    system $curl;
}

# 'hi' file is 37k, so anything smaller is bad
my $size = -s $file;
if ($size < 20000) {
    print "tts.pl: audio file is too small: s=$size f=$file\n";
    unlink $file;
    $file = "/home/bruce/mh/local/data/cache/tts_audio_error_please_try_again";
}

$room = '' if $room eq 'all';

my $server = '192.168.0.150';
my $mqtt1 = Net::MQTT::Simple->new($server);

#system "mosquitto_pub -h 192.168.0.150 -d -t 'mh/$room/speak' -f $file > /dev/null 2>&1";
open (IN, '<', $file); binmode(IN); $/ = undef; my $data = <IN>; 

# Play only 1 file at a time
my $file_lock = "/home/bruce/mh/local/data/cache/tts_mqtt.lock";

while (-e $file_lock) { sleep 1 }
`touch $file_lock`;

#$mqtt1->publish("mh/$room/speak" => $data);
$mqtt1->publish("mh/speak_send" => $data);
sleep 2;
$mqtt1->publish("mh/speak_backup" => $data);

unlink $file_lock;
