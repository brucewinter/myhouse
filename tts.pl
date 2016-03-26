#!/usr/bin/perl

# Simple cached Text To Speech (tts) via http call to various speech engines.

my $text = "@ARGV";

my $file = substr $text, 0, 100;
$file =~ s/\W/_/g;
$file = "/home/bruce/mh/local/data/cache/$file";
$text =~ s/ /\%20/g;

#print "tts db f=$file, t=$text.\n";

unless (-e $file) {

# Other TTS options.  Google switched to using capthas, voicerss voice is not as nice.  Have not tried vocalware
#   my $curl = "curl -s -A 'Mozilla' 'http://translate.google.com/translate_tts?tl=en&client=mh&q=$text' > $file";
#   my $curl = "curl -s -A 'Mozilla' 'http://api.voicerss.org/?key=your_voicerss_key&&hl=en-ca&src=$text' > $file";
# Another option, $3 per 1000 calls: https://www.vocalware.com/support/faq

# Simple IBM watson option, limited to 3 calls a minute.  For more info an an IBM API:
#  https://github.com/watson-developer-cloud/text-to-speech-nodejs
#  http://www.ibm.com/smarterplanet/us/en/ibmwatson/developercloud/text-to-speech.html

    my $curl = "curl -X GET --header 'Accept: audio/wav' 'https://watson-api-explorer.mybluemix.net/text-to-speech/api/v1/synthesize?accept=audio%2Fwav&voice=en-US_MichaelVoice&text=$text' > $file";

#   print "tts db to_file cmd: $curl\n";
    system $curl;
}

system "(mplayer -ao alsa -noconsolecontrols $file > /dev/null 2>&1) &";

