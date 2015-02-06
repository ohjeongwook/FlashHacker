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

		public static function DumpArray(filename:String, refid:String, instruction:String, array:Array):void
		{
			trace("*** DumpArray");
			trace(filename);
			trace(refid);
			trace(instruction);
			for(var i:int=0;i<array.length;i++)
			{
				trace(array[i]);
			}
			trace("");
		}

		public static function DumpByteArray(buffer:ByteArray):String
		{
			var out:String = fillUp("Offset", 8, " ") + "  00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F\n";
			var offset:int = 0;
			var l:int = buffer.length;
			var row:String = "";
			buffer.position = 0;
			for (var i:int = 0; i < l; i += 15)
			{
				 row += fillUp(offset.toString(16).toUpperCase(), 8, "0") + "  ";
				 var n:int = Math.min(16, buffer.length - buffer.position);
				 var string:String = "";
				 for (var j:int = 0; j < 16; ++j)
				 {
					if (j < n)							
					{
							var value:int = buffer.readUnsignedByte();
							string += value >= 32 ? String.fromCharCode(value) : ".";
							row += fillUp(value.toString(16).toUpperCase(), 2, "0") + " ";
							offset++;
					}
					else
					{
							row += "	";
							string += " ";
					}
				 }
				 row += " " + string + "\n";
			}
			out += row;
			return out;
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
