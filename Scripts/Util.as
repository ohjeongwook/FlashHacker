package 
{
	import flash.text.*;
	import flash.utils.*;
	import flash.net.*;

	public class Util
	{
		public function Util() {
		}

		public function Test():void {
			var car:String = "Test";
			var test:Array = new Array();
			test.push(car);
		}

		public static function DumpAPI(filename:String, refid:String, instruction:String, array:Array):void
		{
			trace("        API:" + instruction);
			trace("            From: "+filename + "\t" + refid);

			for(var i:int=0;i<array.length;i++)
			{
				var className:String = getQualifiedClassName( array[i] );
				trace("* " +className + ":");

				if(className=="String")
				{
					trace(array[i]);
				}else if(className=="flash.utils::ByteArray")
				{
					trace(DumpByteArray(array[i]));
				}
				else
				{
					trace(array[i]);
				}
			}
			trace("");
		}

		public static function DumpByteArray(buffer:ByteArray):String
		{
			var lines:String = fillUp("Offset", 8, " ") + "  00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F\n";
			var offset:int = 0;
			var l:int = buffer.length;
			var origPosition:uint = buffer.position;
			buffer.position = 0;
			
			for (var i:int = 0; i < l; i += 16)
			{
				lines += fillUp(offset.toString(16).toUpperCase(), 8, "0") + "  ";
				var line_max:int = Math.min(16, buffer.length - buffer.position);
				var ascii_line:String = "";

				for (var j:int = 0; j < 16; ++j)
				{
					if (j < line_max)							
					{
						var value:int = buffer.readUnsignedByte();
						ascii_line += value >= 32 ? String.fromCharCode(value) : ".";
						lines += fillUp(value.toString(16).toUpperCase(), 2, "0") + " ";
						offset++;
					}
					else
					{
						lines += "   ";
					}
				}
				lines += " " + ascii_line + "\n";
			}

			buffer.position = origPosition;
			return lines;
		}
				
		private static function fillUp(value:String, count:int, fillWith:String):String
		{
			var l:int = count - value.length;
			var ret:String = "";
			while (--l > -1)
				ret += fillWith;
			return ret + value;
		}
	}
}
