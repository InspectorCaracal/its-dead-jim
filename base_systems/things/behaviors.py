# TODO: make do_consume a general use thing, 

from core.ic.behaviors import Behavior, behavior

@behavior
class Consumable(Behavior):
	priority = 1

	def consume(obj, doer, uses=1):
		if uses < 1:
			return ''
		delete_me = []
		damage = False
		if not (stat := obj.stats.get('quantity')):
			stat = obj.stats.integrity
			damage = True
		portions = stat.max
		remaining = stat.value
		quantity = min(uses, remaining)
		if (remaining - quantity) > 0:
			# there will be some left over
			qword = "some of"
		else:
			# there will be none left over
			if portions == 1:
				# not a portionable item
				qword = ""
			elif quantity == portions:
				# we're eating the whole thing at once
				qword = "all of"
			else:
				# we're eating whatever was left
				qword = "the rest of"

		duration = 120
		# apply nutritional duration modifiers here
		# and then apply the moodlets for the duration

		satiation = obj.db.sat or 0
		for o in obj.parts.all():
			satiation += o.db.sat or 0
			sub_dmg = False
			if not (sub_stat := o.stats.get('quantity')):
				sub_stat = o.stats.integrity
				sub_dmg = True
			dmg = quantity * (sub_stat.max / portions)
			if sub_dmg:
				o.at_damage(dmg, destructive=True, quiet=True)
			else:
				sub_stat.current -= dmg
				if sub_stat.value <= 0:
					delete_me.append(o)
		if satiation:
			doer.life.hunger -= satiation * quantity / portions

		# msg = f"{obj.db.verb}s {qword} $gp(their) {obj.sdesc.get()}."

		if damage:
			obj.at_damage(quantity, destructive=True, quiet=True)
		else:
			stat.current -= quantity
			if stat.value <= 0:
				delete_me.append(obj)

		for o in delete_me:
			o.delete()

		# return strip_extra_spaces(msg)
		return qword